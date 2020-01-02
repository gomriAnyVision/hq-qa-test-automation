import subprocess


class VmManager(object):
    def exec_command(self, command):
        with subprocess.Popen([command], stdout=subprocess.PIPE) as proc:
            return proc.stdout.read()

    def force_stop_vm(self, vm):
        return f"virsh destory {vm}"

    def gracefully_stop_vm(self, vm):
        return f"virsh shutdown {vm}"

    def list_vms(self):
        return f"virsh list" \
               f""

