import paramiko

file_path = "scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: support config to connect to the site and HQ


def disconnect_site_from_hq(site_config, ssh_config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=site_config[0]['site_extarnel_ip'], username=ssh_config['username'],
                # password=ssh_config['password'])
                key_filename=ssh_config['pem_path'])
    sftp = ssh.open_sftp()
    sftp.put(f"{file_path}", f"/tmp/{script_path}", confirm=True)
    stdin, stdout, stderr = ssh.exec_command(f"bash /tmp/{script_path}")
    print(stdout.readlines())


def delete_hq_pod(env_config, ssh_config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=env_config['hq_ip'], username=ssh_config['username'], key_filename=ssh_config['pem_path'])
    stdin, stdout, stderr = ssh.exec_command("kubectl get pod |grep hq | awk '{print $1}'")
    hq_pod_name = stdout.read()
    sanitized_hq_pod_name = hq_pod_name.rstrip().decode("utf-8")
    stdin, stdout, stderr = ssh.exec_command(f"kubectl delete pod {sanitized_hq_pod_name}")
    print(stdout.read().rstrip().decode("utf-8"))




