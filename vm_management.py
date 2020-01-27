import json
from pprint import pprint

import googleapiclient
import requests
from googleapiclient import discovery

from Utils.utils import Utils


class MachineManagement(object):
    def __init__(self, machine_mgmt_service):
        self.service = machine_mgmt_service

    def stop(self, name):
        return self.service.stop(name)

    def start(self, name):
        return self.service.start(name)

    def get(self, name):
        return self.service.get(name)


class VmMgmt(object):
    def _get_allocator_ip(self):
        Util = Utils()
        config = Util.get_config('allocator')
        return config['ip']

    def _get_allocator_url(self):
        return "http://{}:8080/vms".format(self._get_allocator_ip())

    def start(self, name):
        request_url = "http://{}:8080/vms/{}/status".format(self._get_allocator_ip(), name)
        res = requests.post(request_url, data=json.dumps({"power": "on"}))
        assert res.status_code == 200
        return res.json()

    def stop(self, name):
        request_url = "http://{}:8080/vms/{}/status".format(self._get_allocator_ip(), name)
        res = requests.post(request_url, data=json.dumps({"power": "off"}))
        return res

    def get(self, name):
        request_url = "http://{}:8080/vms/{}".format(self._get_allocator_ip(), name)
        res = requests.get(request_url)
        if res.status_code == 200:
            return res.json()['info']['status']
        else:
            return res

    def list_vms(self):
        allocator_url = self._get_allocator_url()
        res = requests.get(allocator_url)
        assert res.status_code == 200
        return res.json()['vms']


class GcpInstanceMgmt(object):
    def __init__(self, project="anyvision-training", zone=""):
        self.service = googleapiclient.discovery.build('compute', 'v1')
        self.project = project
        self.zone = zone

    def list(self, zone="europe-west1-d", filter_by=""):
        result = self.service.instances().list(project="anyvision-training", zone=zone,
                                          filter=filter_by).execute()
        return result['items'] if 'items' in result else None

    # TODO: get the name and zone of the machines to update dynamically
    def stop(self, name):
        request = self.service.instances().stop(project=self.project, zone=self.zone,
                                                instance=name)
        response = request.execute()
        pprint(response)

    def start(self, name):
        request = self.service.instances().start(project=self.project, zone=self.zone,
                                                 instance=name)
        response = request.execute()
        pprint(response)

    def get(self, name):
        request = self.service.instances().get(project=self.project, zone=self.zone,
                                               instance=name)
        response = request.execute()
        pprint(response["status"])



