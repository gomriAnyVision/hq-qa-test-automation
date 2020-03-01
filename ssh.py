import json
import logging

import paramiko

from Utils.logger import myLogger
from Utils.utils import Utils

file_path = "scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: Find a way to know if your running on cloud or VM without user input

"""
Stops the paramiko log from overflowing the logging
"""
logging.getLogger("paramiko").setLevel(logging.WARNING)

ssh_logger = myLogger(__name__)

# TODO: Remove duplicated ssh connection code and ssh data parasing
# TODO: Create Retry soluation for connecting via ssh


def disconnect_site_from_hq(**config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=config['site_extarnel_ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'])
    sftp = ssh.open_sftp()
    sftp.put(f"{file_path}", f"/tmp/{script_path}", confirm=True)
    stdin, stdout, stderr = ssh.exec_command(f"bash /tmp/{script_path}")
    print(stdout.readlines())


def _get_pod_name(name):
    return "kubectl get po --selector=app=hq --no-headers " \
           "| grep -iv Terminating | awk {'print $1'}" if name == "hq" \
        else "kubectl get pod |grep api- | awk '{print $1}'"


def delete_pod(**config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=config['ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'],)
    command = _get_pod_name(name=config['pod_name'])
    stdin, stdout, stderr = ssh.exec_command(command)
    hq_pod_name = stdout.read()
    sanitized_hq_pod_name = hq_pod_name.rstrip().decode("utf-8")
    stdin, stdout, stderr = ssh.exec_command(f"kubectl delete pod {sanitized_hq_pod_name}")
    print(stdout.read().rstrip().decode("utf-8"))


def exec_get_site_id(**config):
    command = """echo $(kubectl get secret mongodb-secret --template={{.data.password}} | base64 --decode) |xargs -I '{}' kubectl exec -i mongodb-replicaset-1 -- bash -c "mongo -u root -p '{}' --host mongodb://mongodb-replicaset-0,mongodb-replicaset-1,mongodb-replicaset-2/admin?replicaSet=rs0 --quiet --eval \\\"db.getSiblingDB('mapi').sites.findOne()\\\"" | grep _id | sed -n -e 's/^.*ObjectId("//p' | sed -n -e 's/"),//p'"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=config['ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'], )
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8')
    return result


def exec_get_sync_status(**config):
    command = """ACTIVE_MONGO=$(kubectl get po --selector=app=mongodb-replicaset --no-headers| grep -iv Terminating | awk {'print $1'} | head -1)
echo $(kubectl get secret mongodb-secret --template={{.data.password}} | base64 --decode) | xargs -I '{}' kubectl exec -i $ACTIVE_MONGO -- bash -c "mongo -u root -p '{}' --host mongodb://mongodb-replicaset-0,mongodb-replicaset-1,mongodb-replicaset-2/admin?replicaSet=rs0 --quiet --eval \\\"db.getSiblingDB('mapi').sites.findOne()\\\"" | grep status"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=config['ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'], )
    stdin, stdout, stderr = ssh.exec_command(command)
    sanitized_output = stdout.read().rstrip().decode('utf-8')
    split_sync = sanitized_output.split()
    if split_sync:
        result = split_sync[2].replace('"', '')
        print(f"exec get sync status: {result == 'synced'}")
        return result
    elif not split_sync:
        print(f"exec get sync status split_sync: {split_sync} was empty")


def gravity_cluster_status(logger, ip):
    command = "gravity status --output json"
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    decode_out = stdout.read().decode("utf-8")
    json_output = json.loads(decode_out)
    current_status = [status['status'] for status in json_output['cluster']['nodes']]
    logger.info(f"gravity_cluster_status: {current_status}")
    cluster_status = []
    for node in json_output['cluster']['nodes']:
        if node['status'] == "healthy":
            cluster_status.append(node['status'])
    return cluster_status


def k8s_cluster_status(ip):
    command = "kubectl get no --no-headers | grep -iv NotReady | wc -l"
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    running_nodes = stdout.read().decode("utf-8")
    return running_nodes


def consul_elected_leader(logger, ip):
    command = """kubectl exec -ti $(kubectl get pod -l=app=hq | grep -v Terminating | grep -i 2/2 | awk {'print $1'}
) -c api-master -- curl http://consul-server-client:8500/v1/status/leader"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8')
    print(result)
    return True if result else False


def _ssh_connect(hostname):
    utils = Utils()
    utils.get_args()
    utils.load_config(utils.args.config)
    ssh_config = utils.config['vm'][0]['ssh']
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname,
                username=ssh_config['username'],
                password=ssh_config['password'],
                key_filename=None if ssh_config['pem_path'] == "" else ssh_config['pem_path'])
    return ssh


def hq_pod_healthy(logger, ip):
    command = "kubectl get pod -l=app=hq | grep -v Terminating | grep -i 2/2 | awk {\'print $1\'}"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read()
    result = result.decode("utf-8")
    logger.info(f"hq_pod_healthy - result:{result}")
    return True if result else False


def mongo_has_primary(ip):
    command = """ACTIVE_MONGO=$(kubectl get po --selector=app=mongodb-replicaset --no-headers| grep -iv Terminating | grep -iv Pending | awk {'print $1'} | head -1)
echo $(kubectl get secret mongodb-secret --template={{.data.password}} | base64 --decode) | xargs -I '{}' kubectl exec -i $ACTIVE_MONGO -- bash -c "mongo -u root -p '{}' --host mongodb://mongodb-replicaset-0,mongodb-replicaset-1,mongodb-replicaset-2/admin?replicaSet=rs0 --quiet --eval \\\"rs.status()\\\"" | grep -i primary
    """
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read()
    result = result.decode("utf-8")
    return True if result else False


def consul_nodes(logger, ip):
    command = """kubectl exec -ti $(kubectl get pod -l=app=hq | grep -v Terminating | grep -i 2/2 | awk {'print $1'}
) -c api-master -- curl http://consul-server-client:8500/v1/catalog/nodes"""
    ssh = _ssh_connect(hostname=ip)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read()
    if result:
        decoded_res = result.decode('utf-8')
        json_res = json.loads(decoded_res)
        number_of_peers = len(json_res)
        logger.debug(f"Result: {decoded_res}")
        logger.debug(f"Number of peers: {number_of_peers}")
        return number_of_peers
    else:
        return 0


def machine_reboot(ip):
    ssh_exec_command(ip, cmd="/sbin/reboot -f > /dev/null 2>&1 &",)


def ssh_exec_command(ip, cmd):
    ssh_logger.info(f"Attempting to connect to: {ip}")
    ssh = _ssh_connect(hostname=ip)
    ssh_logger.info(f"Successfully connected to: {ip} - \nExecuting command: '{cmd}'")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read()
    ssh_logger.info(f"Executing command: '{cmd}' on: {ip}, resulted with result: {result}")
    # TODO: Write some parser for different command results
    result = result.decode("utf-8")
    return result if result else False


if __name__ == '__main__':
    command = "/sbin/reboot -f > /dev/null 2>&1 &"
    ssh_exec_command("192.168.21.222", command)
