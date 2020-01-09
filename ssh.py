import paramiko

file_path = "/home/qa-machine/projects/hq-qa-test-automation/scripts/remove_from_site.sh"
script_path = "remove_from_site.sh"

# TODO: support config to connect to the site and HQ


def disconnect_site_from_hq(config=""):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname="35.205.55.158", username="anyvision-devops",
                key_filename="/home/qa-machine/Downloads/anyvision-devops.pem")
    sftp = ssh.open_sftp()
    sftp.put(f"{file_path}",
             f"/tmp/{script_path}", confirm=True)
    stdin, stdout, stderr= ssh.exec_command(f"bash /tmp/{script_path}")
    print(stdout.readlines())
