from pprint import pformat
import time

from Utils.mongodb import MongoDB
from Utils.logger import Logger
from Utils.utils import Utils
from socketio_client import verify_recognition_event
from ssh import disconnect_site_from_hq, delete_pod
from hq import HQ
from site_api import play_forensic


if __name__ == '__main__':
    """
    Config section
    """
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
    hq_session = HQ()
    mongo_client = MongoDB(mongo_password=mongo_config['hq_pass'],
                           mongo_user=mongo_config['hq_user'],
                           mongo_host_port_array=mongo_config['mongo_service_name'])
    for site in env_config:
        # Deleting site before trying to add it again
        logger.info(f"Attempting to delete site: {pformat(site)}")
        sites_id = mongo_client.get_sites_id()
        remove_site_from_hq = hq_session.remove_site(sites_id)
        logger.info(f"Delete site from HQ results: {pformat(remove_site_from_hq)}")
        delete_pod(env_config[0], ssh_config)
        # Attempting to add site again after deleting
        disconnect_site = disconnect_site_from_hq(env_config, ssh_config)
        logger.info(f"Delete site from site results: {disconnect_site}")
        feature_toggle_master = hq_session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
        logger.info(f"Connect to consul at {site['site_consul_ip']} "
                    f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
        if feature_toggle_master == "false":
            hq_session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
            logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true', sleeping 4m seconds to let "
                        f"API restart properly")
            time.sleep(120)
            logger.info("Finished sleeping")
        sites_id = hq_session.add_site(site)
        logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                    f"and external IP {site['site_extarnel_ip']}")
        # time_to_sleep = 120
        # logger.info(f"Sleeping {time_to_sleep} seconds after adding site")
        # time.sleep(time_to_sleep)
    sync_status = {"status": ""}
    while not sync_status['status'] == "synced":
        time.sleep(10)
        sync_status = mongo_client.site_sync_status()
    # time.sleep(180)
    # hq_session.add_subject()
    # play_forensic(env_config)
    # logger.error(f"Site isn't synced ")
    verify_recognition_event(logger, sleep=60)
    for site in env_config:
        sites_id = mongo_client.get_sites_id()
        logger.info(f"Attempting to delete site: {site}")
        remove_site_from_hq = hq_session.remove_site(sites_id)
        disconnect_site = disconnect_site_from_hq(env_config, ssh_config)
        logger.info(f"Delete site from HQ results: {remove_site_from_hq}")
        logger.info(f"Delete site from site results: {disconnect_site}")

