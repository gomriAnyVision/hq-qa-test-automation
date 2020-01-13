from pprint import pprint

import googleapiclient
import requests
from googleapiclient import discovery
from Utils.utils import Utils

service = googleapiclient.discovery.build('compute', 'v1')


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


def list_machines_gcp(zone="europe-west1-d"):
    result = service.instances().list(project="anyvision-training", zone=zone, ).execute()
    return result['items'] if 'items' in result else None

# TODO: get the name and zone of the machines to update dynamically
def stop_gcp_machine(name, zone):
    request = service.instances().stop(project="anyvision-training", zone=zone,
                                       instance=name)
    response = request.execute()
    pprint(response)


def start_gcp_machine(name, zone):
    request = service.instances().start(project="anyvision-training", zone=zone,
                                        instance=name)
    response = request.execute()
    pprint(response)
