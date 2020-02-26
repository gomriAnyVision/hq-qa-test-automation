import sys
import time

from pprint import pformat

from consul import consul_get_one, consul_set
from Utils.logger import Logger
from Utils.utils import Utils, wait_for, calculate_average, active_ip
from ssh import disconnect_site_from_hq, delete_pod
from hq import HQ
from vm_management import MachineManagement, VmMgmt, stop_machine, start_machine, healthy_cluster
from socketio_client import verify_recognition_event
from site_api import play_forensic, is_service_available

SYNC_STATUS = None


def delete_site(active_hq_node):
    sites_id = hq_session.get_sites_id()
    try:
        remove_site_from_hq = hq_session.remove_site(sites_id)
        logger.info(f"Delete site from HQ results: {remove_site_from_hq}")
    except:
        logger.info(f"Nothing to delete result from get_sites_id: {sites_id}")
    disconnect_site = disconnect_site_from_hq(site_extarnel_ip=env_config[0]['site_extarnel_ip'],
                                              username=env_config[0]['ssh']['username'],
                                              password=env_config[0]['ssh']['password'],
                                              pem_path=env_config[0]['ssh']['pem_path'])
    logger.debug(f"Attempting connection to {active_hq_node}")
    logger.info(f"Attemping to disconnect site from HQ")
    delete_pod(ip=active_hq_node,
               username=env_config[0]['ssh']['username'],
               password=env_config[0]['ssh']['password'],
               pem_path=env_config[0]['ssh']['pem_path'],
               pod_name="hq")
    logger.info(f"Delete site from site results: {disconnect_site}")
    logger.info("No sites to delete")


if __name__ == '__main__':
    Logger = Logger()
    utils = Utils()
    logger = Logger.get_logger()
    args = utils.get_args()
    utils.load_config(args.config)
    logger.info(f"Starting tests with {args}")
    env_config = utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    hq_machines = utils.get_config("hq_machines")
    logger.info(f"Received config: {pformat(hq_machines)}")
    machine_mgmt = MachineManagement(VmMgmt())
    wait_for_cluster = 0
    """Cleaning up before starting test by removing all sites which are connected to the HQ
    And starting all stopped nodes"""
    logger.info(f"Setup the machine_mgmt class {machine_mgmt}")
    if machine_mgmt.ensure_all_machines_started(logger):
        wait_for(wait_for_cluster, "Sleeping after starting all machines", logger)
    active_hq_node = active_ip(hq_machines)
    healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
    hq_session = HQ()
    hq_session.login()
    if args.remove_site:
        delete_site(active_hq_node)
    failed_to_add_site_counter = 0
    iteration_number = 0
    timings = []
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    while True:
        for machine, ip in hq_machines.items():
            logger.info(f"Successfully iteration: {iteration_number} "
                        f"Failed iteration: {failed_to_add_site_counter} ")
            before_health_check = time.time()
            active_hq_node = active_ip(hq_machines)
            healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
            logger.info(f"Stop machine IP:{ip}, Name: {machine}")
            stop_machine(machine, wait_for_cluster, logger)
            hq_machines[machine] = None
            active_hq_node = active_ip(hq_machines)
            healthy_cluster("Healthy", logger, active_hq_node)
            after_health_check = time.time()
            hc_before_after = after_health_check - before_health_check
            logger.info(f"Time it took to get a healthy cluster back was:"
                        f" {hc_before_after} seconds")
            """Remove the machine we just stopped ip from the active ip list """
            hq_session = HQ()
            hq_session.login()
            hq_session.get_sites()
            for site in env_config:
                # Attempting to add site again after deletion
                feature_toggle_master = consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
                logger.info(f"Connect to consul at {site['site_consul_ip']} "
                            f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
                if feature_toggle_master == "false":
                    consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
                    delete_pod(ip=env_config[0]['site_extarnel_ip'],
                               username=env_config[0]['ssh']['username'],
                               password=env_config[0]['ssh']['password'],
                               pem_path=env_config[0]['ssh']['pem_path'],
                               pod_name="site")
                if is_service_available(env_config[0]["site_extarnel_ip"], 3000) \
                        and is_service_available(env_config[0]["site_extarnel_ip"], 16180):
                    try:
                        logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true'")
                        wait_for(20, "Waiting for api to restart after feature toggle master", logger)
                        site_id = hq_session.add_site(site)
                        logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                                    f"and external IP {site['site_extarnel_ip']}")
                    except:
                        logger.error(f"Failed to add site with with external IP {site['site_extarnel_ip']} "
                                     f"Attempting to run the automation again")
                        if args.stop_nodes:
                            start_machine(machine, wait_for_cluster, logger)
                        """Add back the machine we just started ip to the active ip list """
                        hq_machines[machine] = ip
                        failed_to_add_site_counter += 1
                        continue
            if failed_to_add_site_counter > 0:
                continue
            while not SYNC_STATUS == "synced":
                time.sleep(10)
                SYNC_STATUS = hq_session.get_sync_status()
                logger.debug(f"Sync status was: {SYNC_STATUS} sleeping 10 seconds and trying again")
            logger.info(f"Site sync status: {SYNC_STATUS}")
            logger.debug(f"Site subjects: {len(hq_session.get_subject_ids())}")
            try:
                logger.info("Playing forensic video in order to create recognition event in HQ")
                play_forensic(env_config[0]['site_extarnel_ip'])
                verify_recognition_event(sleep=60)
            except:
                logger.error("Failed to get event from HQ")
            time_until_recognitions = time.time()
            hc_stop_to_recog = time_until_recognitions - before_health_check
            logger.info(f"Time from stopping node to the getting recognition event:"
                        f" {hc_stop_to_recog}")
            current_iteration_times = {
                "hc_before_after": hc_before_after,
                "hc_stop_to_recog": hc_stop_to_recog
            }
            timings.append(current_iteration_times)
            if args.remove_site:
                hq_active_node = active_ip(hq_machines)
                delete_site(hq_active_node)
            start_machine(machine, wait_for_cluster, logger)
            """Add back the machine we just started ip to the active ip list """
            hq_machines[machine] = ip
            iteration_number += 1
            logger.info(f"{pformat(timings)}")
            all_hc_before_after = [item['hc_before_after'] for item in timings]
            all_hc_stop_to_recog = [item['hc_stop_to_recog'] for item in timings]
            average_hc_before_after = calculate_average(all_hc_before_after)
            average_hc_stop_to_recog = calculate_average(all_hc_stop_to_recog)
            logger.info(f"average time: hc_before_after - {average_hc_before_after} " 
                        f"average time: hc_stop_to_recog - {average_hc_stop_to_recog} ")
