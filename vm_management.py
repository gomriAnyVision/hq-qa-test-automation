import json
import googleapiclient
import requests

from pprint import pprint
from googleapiclient import discovery

from Utils.utils import Utils, wait_for, get_default_config
from ssh import gravity_cluster_status, k8s_cluster_status, hq_pod_healthy, consul_elected_leader, mongo_has_primary, \
    consul_nodes


class MachineManagement(object):
    def __init__(self, machine_mgmt_service):
        self.service = machine_mgmt_service

    def stop(self, name):
        return self.service.stop(name)

    def start(self, name):
        return self.service.start(name)

    def get(self, name):
        return self.service.get(name)

    def machine_list(self):
        return self.machine_list()

    def list_started_machine(self):
        return self.service.list_started_machine()

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
        for machine_name, values in self.machine_list().items():
            all_machines_status.append(values['status'])
        only_on_machines = list(filter(lambda status: status == 'on', all_machines_status))
        return list(only_on_machines)

    def machine_names(self):
        all_machines_names = []
        for machine_name, values in self.machine_list().items():
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

    def list_machines(self, zone="europe-west1-d", filter_by=""):
        result = self.service.instances()._list_machines(project="anyvision-training", zone=zone,
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


machine_mgmt = MachineManagement(VmMgmt())
config = get_default_config()


def start_machine(machine, wait_timeout, logger):
    machine_mgmt.start(machine)
    logger.info(f"Attempting to start machine: {machine} ")
    machine_current_state = machine_mgmt.get(machine)
    logger.info(f"Machine status: {machine_current_state}")
    while not machine_current_state == "on":
        logger.info(f"sleeping 10 seconds waiting for {machine} to start")
        machine_mgmt.start(machine)
        logger.info(f"Attempting to start machine: {machine} ")
        wait_for(10, "Sleeping 10 seconds waiting for machine to start", logger)
        machine_current_state = machine_mgmt.get(machine)
        logger.info(f"Machine status: {machine_current_state}")
    wait_for(wait_timeout, "Sleeping waiting for machine to start", logger)


def running_hq_node(logger):
    # TODO: Refactor this IMMEDIATELLY IT SUCKS
    hq_machines = config['hq_machines']
    vm_mgr = VmMgmt()
    all_machines = vm_mgr.machine_names()
    running_node_ips = []
    for index, machine in enumerate(all_machines):
        if machine["status"] == "on" and machine['machine_name'] in list(hq_machines.keys()) and len(
                running_node_ips) < 1:
            running_node_ips.append(list(hq_machines.values())[index])
    logger.info(f"Function running_hq_node returned: {running_node_ips[0]}")
    return running_node_ips[0]


def healthy_cluster(health_status, logger, hq_ip, minimum_nodes_running=2):
    ssh_config = config['vm'][0]['ssh']
    logger.info(f"Started health checks on cluster")
    while True:
        logger.info(f"Attempting to connect to {hq_ip} and run health checks")
        ready_nodes_k8s_count = k8s_cluster_status(ip=hq_ip,
                                               username=ssh_config['username'],
                                               password=ssh_config['password'],
                                               pem_path=ssh_config['pem_path'], )
        logger.info(f"K8S ready nodes count: {ready_nodes_k8s_count}")
        hq_pod_health = hq_pod_healthy(logger, ip=hq_ip)
        logger.info(f"HQ pod health: {hq_pod_health}")
        consul_health = consul_elected_leader(logger, ip=hq_ip)
        logger.info(f"Consul health: {consul_health}")
        mongo_health = mongo_has_primary(logger, ip=hq_ip)
        logger.info(f"Mongo health: {mongo_health}")
        if int(ready_nodes_k8s_count) >= minimum_nodes_running and hq_pod_health and \
                consul_health and mongo_health:
            logger.info(
                f"Cluster status hq_pod_health: {hq_pod_health}, consul_health: {consul_health}, mongo_health: {mongo_health} "
                f", k8s ready nodes: {ready_nodes_k8s_count}")
            return True
        else:
            logger.info(
                f"Cluster status hq_pod_health:{hq_pod_health}, consul_health: {consul_health}, monog_health: {mongo_health} "
                f", k8s ready nodes: {ready_nodes_k8s_count}")
            wait_for(10, "Waiting 10 seconds before checking cluster status again", logger)


def stop_machine(machine, wait_timeout, logger, **flags):
    if len(machine_mgmt.list_started_machine()) == 4:
        logger.info(f"Checked that 3 HQ nodes are started, stopping one of them")
        machine_mgmt.stop(machine)
        logger.info(f"Stopping machine: {machine}")
        while machine_mgmt.get(machine) == "on" or machine_mgmt.get(machine) == "RUNNING":
            try:
                machine_mgmt.get(machine)
                if machine_mgmt.get(machine).status_code == 500:
                    logger.info(f"The Machine {machine} was already stopped")
                    break
            except:
                pass
            logger.info(f"{machine} is still up even though it should have stopped sleeping "
                        f"for another 10 seconds")
            wait_for(10, "Sleeping 10 seconds waiting for machine to stop", logger)
    wait_for(wait_timeout, "Sleeping after stopping node", logger)
    # if healthy_cluster("healthy", logger) and flags.get("health_check", None):
    #     logger.info(f"Cluster healthy")
