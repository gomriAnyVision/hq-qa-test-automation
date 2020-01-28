from pprint import pformat
import time

from Utils.mongodb import MongoDB
from Utils.logger import Logger
from Utils.utils import Utils
from ssh import disconnect_site_from_hq, delete_pod, get_hq_ip
from main import HQ
from vm_management import MachineManagement, GcpInstanceMgmt, VmMgmt
from socketio_client import verify_recognition_event, on_mass_mass_import_completed
from site_api import play_forensic

hq_machines = {
    "server5-vm-0": "192.168.122.186",
    "server5-vm-1": "192.168.122.38",
    "server5-vm-2": "192.168.122.190"
}


if __name__ == '__main__':
    Logger = Logger()
    Utils = Utils()
    logger = Logger.get_logger()
    args = Utils.get_args()
    logger.info(f"Starting tests with {args}")
    mongo_config = Utils.get_config("mongo")
    logger.info(f"Received config: {pformat(mongo_config)}")
    env_config = Utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    # gcp_instance_mgmt = GcpInstanceMgmt(zone=machines_info['zone'])
    machine_mgmt = MachineManagement(VmMgmt())
    logger.info(f"Setup the machine_mgmt class {machine_mgmt}")
    while True:
        for machine, ip in hq_machines.items():
            running_hq_node_ip = get_hq_ip(list(hq_machines.values()), ip)
            machine_mgmt.stop(machine)
            logger.info(f"Stopping {machine}")
            while machine_mgmt.get(machine) == "on":
                logger.info(f"{machine} is still up even though it should have stopped sleeping "
                            f"for another 10 seconds")
                time.sleep(10)
            hq_session = HQ()
            for site in env_config:
                sleep_after_stopping_node = 180
                logger.info(f"Sleeping for {sleep_after_stopping_node} seconds after stopping node {machine}")
                time.sleep(sleep_after_stopping_node)
                # Deleting site before trying to add it again
                mongo_client = MongoDB(mongo_password=mongo_config['hq_pass'],
                                       mongo_user=mongo_config['hq_user'],
                                       mongo_host_port_array=mongo_config['mongo_service_name'])
                logger.info(f"Attempting to delete site: {site}")
                sites_id = mongo_client.get_sites_id()
                remove_site_from_hq = hq_session.remove_site(sites_id)
                disconnect_site = disconnect_site_from_hq(site_extarnel_ip=env_config[0]['site_extarnel_ip'],
                                                          username=env_config[0]['ssh']['username'],
                                                          password=env_config[0]['ssh']['password'],
                                                          pem_path=env_config[0]['ssh']['pem_path'])
                delete_pod(ip=running_hq_node_ip,
                           username=env_config[0]['ssh']['username'],
                           password=env_config[0]['ssh']['password'],
                           pem_path=env_config[0]['ssh']['pem_path'],
                           pod_name="hq")
                logger.info(f"Delete site from HQ results: {remove_site_from_hq}")
                logger.info(f"Delete site from site results: {disconnect_site}")
                # Attempting to add site again after deletion
                feature_toggle_master = hq_session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
                logger.info(f"Connect to consul at {site['site_consul_ip']} "
                            f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
                if feature_toggle_master == "false":
                    hq_session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
                    sleep_after_toggle_feature = 30
                    delete_pod(ip=env_config[0]['site_extarnel_ip'],
                               username=env_config[0]['ssh']['username'],
                               password=env_config[0]['ssh']['password'],
                               pem_path=env_config[0]['ssh']['pem_path'],
                               pod_name="site")
                    logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true', sleeping {sleep_after_toggle_feature}"
                                f" seconds to let "
                                f"API restart properly")
                    logger.info("Finished sleeping")
                site_id = hq_session.add_site(site)
                logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                            f"and external IP {site['site_extarnel_ip']}")
            sync_status = {"status": ""}
            while not sync_status['status'] == "synced":
                time.sleep(10)
                sync_status = mongo_client.site_sync_status()
            if args.add_single_subject:
                time.sleep(60)
                hq_session.add_subject()
                logger.info("Subject added from HQ to site")
            print(len(hq_session.get_subject_ids()))
            try:
                logger.info("Playing forensic video in order to create recognition event in HQ")
                play_forensic()
                logger.info("Connecting to HQ dashboard socketio waiting for recognition event")
                verify_recognition_event(logger, sleep=60)
            except:
                logger.error("Failed to get event from HQ")
            for site in env_config:
                logger.info(f"Attempting to delete site: {site}")
                sites_id = mongo_client.get_sites_id()
                remove_site_from_hq = hq_session.remove_site(sites_id)
                disconnect_site = disconnect_site_from_hq(site_extarnel_ip=env_config[0]['site_extarnel_ip'],
                                                          username=env_config[0]['username'],
                                                          password=env_config[0]['password'],
                                                          pem_path=env_config[0]['pem_path'])
                logger.info(f"Delete site from HQ results: {pformat(remove_site_from_hq)}")
                logger.info(f"Delete site from site results: {disconnect_site}")
            machine_mgmt.start(machine)
            logger.info(f"Starting {machine} back utilsp")
            machine_current_state = machine_mgmt.get(machine_mgmt)
            while not machine_current_state == "RUNNING" or "on":
                logger.info(f"sleeping 10 seconds waiting for {machine} to start")
                time.sleep(10)
                machine_current_state = machine_mgmt.get(machine)
            logger.info(f"Sleeping 120 seconds after machine {machine} starts")
            time.sleep(120)