import paramiko

file_path = "/scripts/disconnect_site_from_hq.sh"
script_path = "disconnect_site_from_hq.sh"

# TODO: support config to connect to the site and HQ


def disconnect_site_from_hq(site_config, ssh_config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname=site_config['site_extarnel_ip'], username=ssh_config['username'],
                password=ssh_config['password'])
                # key_filename=ssh_config['pem_path'])
    sftp = ssh.open_sftp()
    sftp.put(f"{file_path}", f"/tmp/{script_path}", confirm=True)
    stdin, stdout, stderr= ssh.exec_command(f"bash /tmp/{script_path}")
    print(stdout.readlines())
