import paramiko

file_path = "scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: Find to know if your running on cloud or VM without user input

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


def delete_hq_pod(**config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=config['hq_ip'],
                username=config['username'],
                password=config['password'],
                key_filename=None if config['pem_path'] == "" else config['pem_path'])
    stdin, stdout, stderr = ssh.exec_command("kubectl get pod |grep hq | awk '{print $1}'")
    hq_pod_name = stdout.read()
    sanitized_hq_pod_name = hq_pod_name.rstrip().decode("utf-8")
    stdin, stdout, stderr = ssh.exec_command(f"kubectl delete pod {sanitized_hq_pod_name}")
    print(stdout.read().rstrip().decode("utf-8"))


