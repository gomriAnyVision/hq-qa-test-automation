from pprint import pprint

import requests

ALLOCATOR_IP = "192.168.21.87"
ALLOCATOR_URL = "http://{}:8080/vms".format(ALLOCATOR_IP)


def update_vm_status(vm_name, power):
    request_url = "http://{}:8080/vms/{}/status".format(ALLOCATOR_IP, vm_name)
    res = requests.post(request_url, data={"power": power})
    assert res.status_code == 200
    return res.json()


def list_vms():
    res = requests.get(ALLOCATOR_URL)
    assert res.status_code == 200
    return res.json()['vms']


if __name__ == '__main__':
    for vm in list_vms():
        pprint(list_vms()[vm])