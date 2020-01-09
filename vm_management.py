from pprint import pprint
import requests

from Utils.utils import Utils


def _get_allocator_ip():
    Util = Utils()
    config = Util.get_config('allocator')
    return config['ip']


def _get_allocator_url():
    return "http://{}:8080/vms".format(_get_allocator_ip())


def update_vm_status(vm_name, power, config):
    request_url = "http://{}:8080/vms/{}/status".format(_get_allocator_ip(), vm_name)
    res = requests.post(request_url, data={"power": power})
    assert res.status_code == 200
    return res.json()


def list_vms():
    allocator_url = _get_allocator_url()
    res = requests.get(allocator_url)
    assert res.status_code == 200
    return res.json()['vms']


if __name__ == '__main__':
    for vm in list_vms():
        pprint(list_vms()[vm])