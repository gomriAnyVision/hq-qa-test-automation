import json
import googleapiclient
import requests

from pprint import pprint
from googleapiclient import discovery

from Utils.utils import Utils
from Utils.logger import Logger


class MachineManagement(object):
    def __init__(self, machine_mgmt_service):
        self.service = machine_mgmt_service

    def stop(self, name):
        return self.service.stop(name)

    def start(self, name):
        return self.service.start(name)

    def get(self, name):
        return self.service.get(name)

    def machine_list(self, *kwargs):
        return self.service.machine_list(*kwargs)

    def list_started_machine(self):
        return self.service.list_stopped_machines()

    def ensure_all_machines_started(self, logger):
        logger.info("Attempting to start all hq nodes")
        return self.service.ensure_all_machines_started(logger)


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

    def machine_list(self):
        allocator_url = self._get_allocator_url()
        res = requests.get(allocator_url)
        assert res.status_code == 200
        return res.json()['vms']

    def list_started_machine(self):
        all_machines_status = []
        for machine_name, values in self.list_machines().items():
            all_machines_status.append(values['status'])
        only_on_machines = list(filter(lambda status: status == 'on', all_machines_status))
        return list(only_on_machines)

    def machine_names(self):
        all_machines_names = []
        for machine_name, values in self.list_machines().items():
            all_machines_names.append({"machine_name": machine_name, "status": values['status']})
        return all_machines_names

    def ensure_all_machines_started(self, logger):
        started_machine_list = self.list_started_machine()
        machines_to_start = [machine for machine in self.machine_names() if machine['status'] == 'off']
        if not machines_to_start:
            return False
        while len(started_machine_list) < 4:
            for machine in machines_to_start:
                self.start(machine['machine_name'])
                started_machine_list = self.list_started_machine()
                logger.info(f"Attempting to start {machine['machine_name']} in order to "
                            f"get back to 3 hq nodes being up for tha test to start properly")


class GcpInstanceMgmt(object):
    def __init__(self, project="anyvision-training", zone=""):
        self.service = googleapiclient.discovery.build('compute', 'v1')
        self.project = project
        self.zone = zone

    def machine_list(self, filter):
        result = self.service.instances().list(project="anyvision-training", zone=self.zone,
                                               filter=filter).execute()
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

    def list_stopped_machines(self):
        machines_to_start = []
        for machine in self.machine_list(filter="labels.auto eq test"):
            if machine['status'] == "TERMINATED":
                machines_to_start.append({"machine_name": machine['name'],
                                          "status": machine['status']})
            else:
                continue
        return machines_to_start

    def list_started_machine(self):
        machines_to_start = []
        for machine in self.machine_list(filter="labels.auto eq test"):
            if machine['status'] == "RUNNING":
                machines_to_start.append({"machine_name": machine['name'],
                                          "status": machine['status']})
            else:
                continue
        return machines_to_start


    def ensure_all_machines_started(self, logger):
        machines_to_start = self.list_stopped_machines()
        while self.list_stopped_machines():
            for machine in machines_to_start:
                self.start(machine['machine_name'])
                machines_to_start = self.list_stopped_machines()
                logger.info(f"Attempting to start {machine['machine_name']} in order to "
                            f"get back to 3 hq nodes being up for tha test to start properly")

if __name__ == '__main__':
    machine_mgmt_service = GcpInstanceMgmt(zone="us-west1-b")
    Logger = Logger()
    Utils = Utils()
    logger = Logger.get_logger()
    # machine_mgmt = MachineManagement(machine_mgmt_service)
    machine_mgmt_service.ensure_all_machines_started(logger)
