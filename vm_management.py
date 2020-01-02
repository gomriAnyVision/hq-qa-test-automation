import subprocess


class VmManager(object):
    def exec_command(self, command):
        with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as proc:
            return proc.stdout.read()

    def list_vms(self, args):
        return f"virsh list {args}"

    def force_shutdown_vm(self,vm):
        return f"virsh destory {vm}"



