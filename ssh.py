import sys

import paramiko
import json
import time
import logging

from Utils.utils import get_default_config, wait_for

file_path = "scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: Find a way to know if your running on cloud or VM without user input

config = get_default_config()
"""
Stop the paramiko logg from overflowing the logging
"""
logging.getLogger("paramiko").setLevel(logging.WARNING)

ssh_logger = logging.getLogger(__name__)
ssh_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
handler = logging.StreamHandler(sys.stdout)
file_handler.setFormatter(formatter)
ssh_logger.addHandler(file_handler)
ssh_logger.addHandler(handler)

# TODO: Remove duplicated ssh connection code and ssh data parasing

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


def gravity_cluster_status(**config):
    command = "gravity status --output json"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=config['ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'])
    stdin, stdout, stderr = ssh.exec_command(command)
    decode_out = stdout.read().decode("utf-8")
    json_output = json.loads(decode_out)
    cluster_status = []
    for node in json_output['cluster']['nodes']:
        cluster_status.append(node['status'])
    return cluster_status if cluster_status else None


def k8s_cluster_status(**config):
    command = "kubectl get no --no-headers | grep -iv NotReady | wc -l"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=config['ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'])
    stdin, stdout, stderr = ssh.exec_command(command)
    running_nodes = stdout.read().decode("utf-8")
    return running_nodes


def consul_elected_leader(logger, **kwargs):
    kwargs['timeout'] = None
    timeout=kwargs['timeout'] if kwargs['timeout'] else 60
    stop_time = time.time() + timeout
    command = """kubectl exec -ti $(kubectl get pod -l=app=hq | grep -v Terminating | grep -i 2/2 | awk {'print $1'}
) -c api-master -- curl http://consul-server-client:8500/v1/status/leader"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_config = config['vm'][0]['ssh']
    ssh.connect(hostname=kwargs['ip'],
                username=ssh_config['username'],
                password=ssh_config['password'],
                key_filename=None if ssh_config['pem_path'] == "" else kwargs['pem_path'])
    while not time.time() > stop_time:
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode('utf-8')
        if not result:
            wait_for(10, "Sleeping while consul isn't healthy", logger)
        else:
            return True
    else:
        logger.error(f"Consul was unhealthy after {timeout} seconds")
        return False


def _ssh_connect(hostname):
    config = get_default_config()
    ssh_config = config['vm'][0]['ssh']
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname,
                username=ssh_config['username'],
                password=ssh_config['password'],
                key_filename=None if ssh_config['pem_path'] == "" else ssh_config['pem_path'])
    return ssh


def hq_pod_healthy(logger, **kwargs):
    kwargs['timeout'] = None
    timeout = kwargs['timeout'] if kwargs['timeout'] else 60
    timeout = time.time() + timeout
    command = "kubectl get pod -l=app=hq | grep -v Terminating | grep -i 2/2 | awk {\'print $1\'}"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_config = config['vm'][0]['ssh']
    ssh.connect(hostname=kwargs['ip'],
                username=ssh_config['username'],
                password=ssh_config['password'],
                key_filename=None if ssh_config['pem_path'] == "" else kwargs['pem_path'])
    while not time.time() > timeout:
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode("utf-8")
        if result:
            return True
        else:
            wait_for(10, "Sleeping while hq isn't healthy", logger)
    return False


def mongo_has_primary(logger, ip, timeout=60):
    timeout = time.time() + timeout
    command = """ACTIVE_MONGO=$(kubectl get po --selector=app=mongodb-replicaset --no-headers| grep -iv Terminating | awk {'print $1'} | head -1)
echo $(kubectl get secret mongodb-secret --template={{.data.password}} | base64 --decode) | xargs -I '{}' kubectl exec -i $ACTIVE_MONGO -- bash -c "mongo -u root -p '{}' --host mongodb://mongodb-replicaset-0,mongodb-replicaset-1,mongodb-replicaset-2/admin?replicaSet=rs0 --quiet --eval \\\"rs.status()\\\"" | grep -i primary
    """
    ssh = _ssh_connect(hostname=ip)
    while not time.time() > timeout:
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode("utf-8")
        if result:
            return True
        else:
            wait_for(10, "Sleeping while mongo hasn't selected primary isn't healthy", logger)
    return False


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
        # TODO: change log level to debug
        logger.debug(f"Result: {decoded_res}")
        logger.debug(f"Number of peers: {number_of_peers}")
        return number_of_peers
    else:
        return 0

