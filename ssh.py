import paramiko


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("34.76.63.166", username="anyvision-devops",
                key_filename="/home/qa-machine/Downloads/anyvision-devops.pem")

    command = "DASH_API_POD=`kubectl get pod | grep ^api- | awk {'print$1'}` ;" \
              " kubectl cp default/${DASH_API_POD}:/home/user/Dash-API/scripts/delete-data-from-api-and-sync.sh /tmp/script > /dev/null 2>&1 ;" \
              " bash /tmp/script"

    stdin, stdout, stderr = ssh.exec_command("DASH_API_POD=`kubectl get pod | grep ^api- | awk {'print$1'}` && echo $DASH_API_POD")
    print(stdout.readlines())

if __name__ == '__main__':
    main()