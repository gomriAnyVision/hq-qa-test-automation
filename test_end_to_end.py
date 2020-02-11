import time

from pprint import pformat
from Utils.logger import Logger
from Utils.utils import Utils, wait_for
from ssh import disconnect_site_from_hq, delete_pod, get_hq_ip, exec_get_site_id, exec_get_sync_status, gravity_cluster_status
from main import HQ
from vm_management import MachineManagement, VmMgmt
from socketio_client import verify_recognition_event
from site_api import play_forensic, is_service_available


def get_sync_status():
    if hq_session.get_sites():
        _, result = hq_session.get_sites()
        logger.warning("This currently only supports one site and need to be changed in case we want to test "
                    "multiple sites with the same HQ")
        if result:
            return result[0]



def get_sites_id():
    if hq_session.get_sites():
        result, _ = hq_session.get_sites()
        if result:
            return result


def delete_site(alive_hq_node_ip):
    sites_id = get_sites_id()
    if sites_id:
        remove_site_from_hq = hq_session.remove_site(sites_id)
        disconnect_site = disconnect_site_from_hq(site_extarnel_ip=env_config[0]['site_extarnel_ip'],
                                                  username=env_config[0]['ssh']['username'],
                                                  password=env_config[0]['ssh']['password'],
                                                  pem_path=env_config[0]['ssh']['pem_path'])
        logger.debug(f"Attempting connection to {alive_hq_node_ip}")
        delete_pod(ip=alive_hq_node_ip,
                   username=env_config[0]['ssh']['username'],
                   password=env_config[0]['ssh']['password'],
                   pem_path=env_config[0]['ssh']['pem_path'],
                   pod_name="hq")
        logger.info(f"Delete site from HQ results: {remove_site_from_hq}")
        logger.info(f"Delete site from site results: {disconnect_site}")
    logger.info("No sites to delete")

def stop_machine(machine):
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
            time.sleep(10)
    if healthy_cluster:
        wait_for(wait_for_cluster, "Sleeping after stopping node", logger)


def start_machine(machine):
    machine_mgmt.start(machine)
    logger.info(f"Attempting to start machine: {machine} ")
    machine_current_state = machine_mgmt.get(machine)
    logger.info(f"Machine status: {machine_current_state}")
    while not machine_current_state == "on":
        logger.info(f"sleeping 10 seconds waiting for {machine} to start")
        machine_mgmt.start(machine)
        logger.info(f"Attempting to start machine: {machine} ")
        time.sleep(10)
        machine_current_state = machine_mgmt.get(machine)
        logger.info(f"Machine status: {machine_current_state}")
    wait_for(wait_for_cluster, "Sleeping waiting for machine to start", logger)


def healthy_cluster(cluster, health_status, minimum_nodes=2):
    cluster_status = None
    while cluster_status != "HEALTHY":
        if cluster and gravity_cluster_status().count(health_status) >= minimum_nodes:
            cluster_status = "HEALTHY"
            return True
        else:
            logger.info(f"Cluster status was: {cluster} - UNHEALTHY")
            return False



if __name__ == '__main__':
    Logger = Logger()
    Utils = Utils()
    logger = Logger.get_logger()
    args = Utils.get_args()
    Utils.set_config(args.config)
    logger.info(f"Starting tests with {args}")
    mongo_config = Utils.get_config("mongo")
    logger.info(f"Received config: {pformat(mongo_config)}")
    env_config = Utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    hq_machines = Utils.get_config("hq_machines")
    logger.info(f"Received config: {pformat(hq_machines)}")
    # gcp_instance_mgmt = GcpInstanceMgmt(zone=machines_info['zone'])
    machine_mgmt = MachineManagement(VmMgmt())
    wait_for_cluster = 120
    """Cleaning up beofore starting test by removing all sites which are connected to the HQ
    And starting all stopped nodes"""
    logger.info(f"Setup the machine_mgmt class {machine_mgmt}")
    if machine_mgmt.ensure_all_machines_started(logger):
        wait_for(wait_for_cluster, "Sleeping after starting all machines", logger)
    hq_session = HQ()
    delete_site(hq_machines["server5-vm-0"])
    failed_to_add_site_counter = 0
    iteration_number = 0
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    while True:
        for machine, ip in hq_machines.items():
            logger.info(f"Successfully iteration: {iteration_number} "
                        f"Failed iteration: {failed_to_add_site_counter}")
            stop_machine(machine)
            running_hq_node_ip = get_hq_ip(list(hq_machines.values()), ip)
            hq_session = HQ()
            hq_session.get_sites()
            for site in env_config:
                # Attempting to add site again after deletion
                feature_toggle_master = hq_session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
                logger.info(f"Connect to consul at {site['site_consul_ip']} "
                            f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
                if feature_toggle_master == "false":
                    hq_session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
                    delete_pod(ip=env_config[0]['site_extarnel_ip'],
                               username=env_config[0]['ssh']['username'],
                               password=env_config[0]['ssh']['password'],
                               pem_path=env_config[0]['ssh']['pem_path'],
                               pod_name="site")
                if is_service_available(env_config[0]["site_extarnel_ip"], 3000) \
                        and is_service_available(env_config[0]["site_extarnel_ip"], 16180):
                    try:
                        logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true'")
                        wait_for(120, "Waiting for api to restart after feature toggle master", logger)
                        site_id = hq_session.add_site(site)
                        logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                                    f"and external IP {site['site_extarnel_ip']}")
                    except:
                        logger.error(f"Failed to add site with with external IP {site['site_extarnel_ip']} "
                                     f"Attempting to run the automation again")
                        start_machine(machine)
                        failed_to_add_site_counter += 1
                        continue
            sync_status = ""
            while not sync_status == "synced":
                time.sleep(10)
                sync_status = get_sync_status()
            if args.add_single_subject:
                wait_for(60, "Sleeping after adding subject", logger)
                hq_session.add_subject()
                logger.info("Subject added from HQ to site")
            logger.debug(f"Site subjects: {len(hq_session.get_subject_ids())}")
            try:
                logger.info("Playing forensic video in order to create recognition event in HQ")
                play_forensic(env_config)
                logger.info("Connecting to HQ dashboard socketio waiting for recognition event")
                verify_recognition_event(logger, sleep=60)
            except:
                logger.error("Failed to get event from HQ")
            for site in env_config:
                delete_site(running_hq_node_ip)
            start_machine(machine)
            iteration_number += 1
