from Utils.mongodb import MongoDB
from Utils.logger import Logger
from Utils.utils import Utils
from ssh import disconnect_site_from_hq
from vm_management import update_vm_status
from main import HQ

import time


hq_vms = []

if __name__ == '__main__':
    Logger = Logger()
    Utils = Utils()
    logger = Logger.get_logger()
    args = Utils.get_args()
    logger.info(f"Starting tests with {args}")
    env_config = Utils.get_config(args.env)
    logger.info(f"Received config: {env_config}")
    ssh_config = Utils.get_config('ssh')
    logger.info(f"Received config: {ssh_config}")
    while True:
        for vm in hq_vms:
            update_vm_status(vm, "off")

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

