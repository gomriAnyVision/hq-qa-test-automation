import paramiko

file_path = "scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: Find to know if your running on cloud or VM without user input

def is_cloud():
    pass


def disconnect_site_from_hq_V2(host, username, password, key_filename):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=host,
                username=None if is_cloud() else username,
                password=None if is_cloud() else username,
                key_filename=None if config['pem_path'] == "" else config['pem_path'])
    sftp = ssh.open_sftp()
    sftp.put(f"{file_path}", f"/tmp/{script_path}", confirm=True)
    stdin, stdout, stderr = ssh.exec_command(f"bash /tmp/{script_path}")
    print(stdout.readlines())


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


def get_hq_ip(ips, ip_of_stoped):
    ips.remove(ip_of_stoped)
    return ips[0]


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
                key_filename=None if config['pem_path'] == "" else config['pem_path'],
                )
    command = _get_pod_name(name=config['pod_name'])
    stdin, stdout, stderr = ssh.exec_command(command)
    hq_pod_name = stdout.read()
    sanitized_hq_pod_name = hq_pod_name.rstrip().decode("utf-8")
    stdin, stdout, stderr = ssh.exec_command(f"kubectl delete pod {sanitized_hq_pod_name}")
    print(stdout.read().rstrip().decode("utf-8"))


