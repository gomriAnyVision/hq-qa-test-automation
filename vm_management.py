import json
import time
import googleapiclient
import requests

from paramiko.ssh_exception import NoValidConnectionsError
from pprint import pprint
from googleapiclient import discovery

from Utils.logger import myLogger
from Utils.utils import Utils, wait_for
from hq import HQ
from consul import consul_get_all_nodes_healthcheck, verify_all_consul_members_alive,\
    consul_get_with_consistency, consul_get_leader
from ssh import k8s_cluster_status, hq_pod_healthy, mongo_has_primary, \
    consul_nodes, gravity_cluster_status


vm_management_logger = myLogger(__name__)

class MachineManagement(object):
    def __init__(self, machine_mgmt_service):
        self.service = machine_mgmt_service

    def ensure_all_machines_started(self, logger):
        logger.info("Attempting to start all hq nodes")
        return self.service.ensure_all_machines_started(logger)


class VmMgmt(object):
    def _get_allocator_ip(self):
        utils = Utils()
        args = utils.get_args()
        utils.load_config(args.config)
        config = utils.get_config('allocator')
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
        try:
            for machine_name, values in self.machine_list().items():
                all_machines_status.append(values['status'])
        except AttributeError:
            for machine in self.machine_list():
                all_machines_status.append(machine['status'])
        only_on_machines = list(filter(lambda status: status == 'on', all_machines_status))
        return list(only_on_machines)

    def machine_names(self):
        all_machines_names = []
        try:
            for machine_name, values in self.machine_list().items():
                all_machines_names.append({"machine_name": machine_name, "status": values['status']})
        except AttributeError:
            for machine in self.machine_list():
                all_machines_names.append({"machine_name": machine['name'], "status": machine['status']})
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


machine_mgmt = VmMgmt()
utils = Utils()
utils.get_args()
config = utils.load_config(utils.args.config)


def start_machine(machine, wait_timeout,):
    machine_mgmt.start(machine)
    vm_management_logger.info(f"Attempting to start machine: {machine} ")
    machine_current_state = machine_mgmt.get(machine)
    vm_management_logger.info(f"Machine status: {machine_current_state}")
    while not machine_current_state == "on":
        vm_management_logger.info(f"sleeping 10 seconds waiting for {machine} to start")
        machine_mgmt.start(machine)
        vm_management_logger.info(f"Attempting to start machine: {machine} ")
        wait_for(10, "Sleeping 10 seconds waiting for machine to start", vm_management_logger)
        machine_current_state = machine_mgmt.get(machine)
        vm_management_logger.info(f"Machine status: {machine_current_state}")
    wait_for(wait_timeout, "Sleeping waiting for machine to start", vm_management_logger)


def healthy_cluster(health_status, logger, hq_ip, minimum_nodes_running=2):
    logger.info(f"Started health checks on cluster")
    while True:
        try:
            wait_for(10, "Waiting to start health checks again",logger)
            logger.info(f"Attempting to connect to {hq_ip} and run health checks")
            gravity_ready_nodes = gravity_cluster_status(logger, hq_ip)
            logger.info(f"gravity_ready_nodes: {gravity_ready_nodes}")
            if len(gravity_ready_nodes) < minimum_nodes_running:
                logger.error(f"Failed get enough gravity nodes: {len(gravity_ready_nodes)}")
                continue
            ready_nodes_k8s_count = k8s_cluster_status(hq_ip)
            logger.info(f"K8S ready nodes count: {ready_nodes_k8s_count}")
            if int(ready_nodes_k8s_count) < minimum_nodes_running:
                logger.error(f"ready_nodes_k8s_count: {ready_nodes_k8s_count}")
                continue
            consul_active = consul_get_with_consistency(logger, hq_ip, "HQ_HA_TESTING_AUTOMATION/TEST", str(time.time()))
            logger.info(f"consul_get_with_consistency: {consul_active}")
            if not consul_active:
                logger.error(f"Failed on consul_active: {consul_active}")
                continue
            hq_pod_health = hq_pod_healthy(logger, ip=hq_ip)
            logger.info(f"HQ pod health: {hq_pod_health}")
            if not hq_pod_health:
                logger.error(f"Failed to find healthy hq pod hq_pod_healthy returned: {hq_pod_health}")
                continue
            consul_elected_leader = consul_get_leader(logger, ip=hq_ip)
            logger.info(f"Consul elected leader: {consul_elected_leader}")
            if not consul_get_leader:
                logger.error(f"Consul failed to elect leader consul_elected_leader: {consul_elected_leader}")
                continue
            mongo_health = mongo_has_primary(ip=hq_ip)
            logger.info(f"Mongo health: {mongo_health}")
            if not mongo_health:
                logger.error(f"Failed to find mongo leader mongo_health returned: {mongo_health}")
                continue
            ready_consul_nodes = consul_nodes(logger, ip=hq_ip)
            logger.info(f"Ready consul nodes: {ready_consul_nodes}")
            if ready_consul_nodes < minimum_nodes_running:
                logger.error(f"Failed to find enough consul nodes running "
                             f"ready_consul_nodes returned: {ready_consul_nodes}")
                continue
            ready_hc_consul_nodes = consul_get_all_nodes_healthcheck(ip=hq_ip, num_servers=minimum_nodes_running)
            logger.info(f"Health consul nodes amount: {ready_hc_consul_nodes}")
            if not ready_hc_consul_nodes:
                logger.error(f"Failed to find enough consul nodes healthy "
                             f"ready_hc_consul_nodes returned: {ready_hc_consul_nodes}")
                continue
            consul_active_members = verify_all_consul_members_alive(hq_ip)
            logger.info(f"Ready active member nodes: {consul_active_members}")
            if consul_active_members < minimum_nodes_running:
                logger.error(f"Failed to find enough active consul member nodes "
                             f"consul_active_members returned: {consul_active_members}")
                continue
            hq_session = HQ()
            hq_login_res = hq_session.login()
            logger.info(f"HQ login result {hq_login_res}")
            if not hq_login_res:
                logger.error(f"Failed to login to HQ hq_login_res returned: {hq_login_res}")
                continue
            return
        except NoValidConnectionsError:
            logger.error('Failed to login')
            wait_for(10, f"Failed to SSH to: {hq_ip}, waiting 10 seconds ", logger)


def stop_machine(machine, method="stop", ip=None):
    if len(machine_mgmt.list_started_machine()) == 4:
        vm_management_logger.info(f"Checked that 3 HQ nodes are started, stopping one of them")
        # if method == "stop":
        machine_mgmt.stop(machine)
        # elif method == "restart":
        #     reboot(ip)
        vm_management_logger.info(f"Stopping machine: {machine}")
        while machine_mgmt.get(machine) == "on" or machine_mgmt.get(machine) == "RUNNING":
            try:
                machine_mgmt.get(machine)
                if machine_mgmt.get(machine).status_code == 500:
                    vm_management_logger.info(f"The Machine {machine} was already stopped")
                    break
            except:
                pass
            vm_management_logger.info(f"The Machine {machine} is still up even though it should have stopped sleeping "
                                      f"for another 10 seconds")
            wait_for(10, "Sleeping 10 seconds waiting for machine to stop", logger)
