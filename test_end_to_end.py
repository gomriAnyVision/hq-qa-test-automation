from pprint import pformat
import time

from Utils.mongodb import MongoDB
from Utils.logger import Logger
from Utils.utils import Utils
from ssh import disconnect_site_from_hq
from main import HQ
from vm_management import stop_gcp_machine, start_gcp_machine, get_gcp_machine, update_vm_status
from socketio_client import verify_recognition_event, on_mass_mass_import_completed
from site_api import play_forensic, verify_subject_in_site


machines_info = {
    "hq_machines": [
        "omri-hq-ha-3-i-europe-west1-d-1",
        "omri-hq-ha-3-i-europe-west1-d-2",
        "omri-hq-ha-3-i-europe-west1-d-3"
    ],
    "zone": "europe-west1-d"
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
    ssh_config = Utils.get_config('ssh')
    logger.info(f"Received config: {pformat(ssh_config)}")
    while True:
        for machine in machines_info["hq_machines"]:
            if args.env == "cloud":
                stop_gcp_machine(machine, machines_info['zone'])
                logger.info(f"Stopping {machine}")
                while get_gcp_machine(machine, machines_info['zone']) == "RUNNING":
                    logger.info(f"{machine} is still up even though it should have stopped sleeping "
                                f"for another 10 seconds")
                    time.sleep(10)
            else:
                update_vm_status(machine, "off")
            hq_api = HQ()
            for site in env_config:
                feature_toggle_master = hq_api.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
                logger.info(f"Connect to consul at {site['site_consul_ip']} "
                            f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
                if feature_toggle_master == "false":
                    hq_api.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
                    logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true', sleeping 60 seconds to let "
                                f"API restart properly")
                    time.sleep(60)
                    logger.info("Finished sleeping")
                site_id = hq_api.add_site(site)
                logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                            f"and external IP {site['site_extarnel_ip']}")
            mongo_client = MongoDB(mongo_password=mongo_config['hq_pass'],
                                   mongo_user=mongo_config['hq_user'],
                                   mongo_host_port_array=mongo_config['mongo_service_name'])
            mongo_client.site_sync_status("mapi")
            hq_api.add_subject()
            if verify_subject_in_site():
                logger.info("Subject added from HQ to site")
                logger.info("Playing forensic video in order to create recognition event in HQ")
                play_forensic()
                logger.info("Connecting to HQ dashboard socketio waiting for recognition event")
                verify_recognition_event()
            else:
                logger.error("Failed to add subject from hq to site")


            # for site in env_config:
            #     logger.info(f"Attempting to delete site: {site}")
            #     remove_site_from_hq = hq_api.remove_site(site)
            #     disconnect_site = disconnect_site_from_hq(env_config, ssh_config)
            #     logger.info(f"Delete site from HQ results: {pformat(remove_site_from_hq)}")
            #     logger.info(f"Delete site from site results: {disconnect_site}")

