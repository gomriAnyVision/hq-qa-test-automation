from pprint import pprint

import googleapiclient
import requests
from googleapiclient import discovery

from Utils.utils import Utils

service = googleapiclient.discovery.build('compute', 'v1')


class MachineManagement(object):
    def __init__(self, machine_mgnt_service):
        self.service = machine_mgnt_service

    def stop(self, name):
        return self.service.stop(name)

    def start(self, name):
        return self.service.start(name)

    def get(self, name):
        return self.service.get(name)


class VmMgnt(object):

    def _get_allocator_ip(self):
        Util = Utils()
        config = Util.get_config('allocator')
        return config['ip']

    def _get_allocator_url(self):
        return "http://{}:8080/vms".format(self._get_allocator_ip())

    def update_vm_status(self, vm_name, power):
        request_url = "http://{}:8080/vms/{}/status".format(self._get_allocator_ip(), vm_name)
        res = requests.post(request_url, data={"power": power})
        assert res.status_code == 200
        return res.json()

    def list_vms(self):
        allocator_url = self._get_allocator_url()
        res = requests.get(allocator_url)
        assert res.status_code == 200
        return res.json()['vms']


class GcpInstanceMgnt(object):
    def __init__(self, project="anyvision-training", zone=""):
        self.project = project
        self.zone = zone

    def list(self, zone="europe-west1-d", filter_by=""):
        result = service.instances().list(project="anyvision-training", zone=zone,
                                          filter=filter_by).execute()
        return result['items'] if 'items' in result else None

    # TODO: get the name and zone of the machines to update dynamically
    def stop(self, name):
        request = service.instances().stop(project=self.project, zone=self.zone,
                                           instance=name)
        response = request.execute()
        pprint(response)

    def start(self, name):
        request = service.instances().start(project=self.project, zone=self.zone,
                                            instance=name)
        response = request.execute()
        pprint(response)

    def get(self, name):
        request = service.instances().get(project=self.project, zone=self.zone,
                                          instance=name)
        response = request.execute()
        pprint(response["status"])


if __name__ == '__main__':
    gcp_instance_mgnt = GcpInstanceMgnt(zone="us-west1-b")
    machine_mgnt = MachineManagement(gcp_instance_mgnt)
    machine_mgnt.stop("aharon-hq-ha-d-us-west1-b-2")


