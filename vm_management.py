from pprint import pprint

import requests


def update_vm_status(vm_name, power, config):
    request_url = "http://{}:8080/vms/{}/status".format(config['allocator_ip'], vm_name)
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