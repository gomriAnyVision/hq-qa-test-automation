import logging
import sys

from Utils.logger import myLogger
from Utils.utils import wait_for, get_ssh_params
from consul import consul_get_one, consul_set
from site_api import is_service_available
from socketio_client import verify_recognition_event
from ssh import disconnect_site_from_hq, delete_pod

tasks_logger = myLogger(__name__)


def wait_for_recog():
    while True:
        try:
            tasks_logger.info("Started waiting for recognition event")
            recog_event_count = verify_recognition_event(sleep=60)
            if recog_event_count['on_recognition'] <= 0:
                continue
            else:
                return True
        except:
            tasks_logger.error("Failed to get event from HQ")


def wait_for_add_site(hq_session, config):
    while True:
        if not hq_session.login():
            continue
        username, pem_path, password, site_extarnel_ip = get_ssh_params(config)
        feature_toggle_master = consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site_extarnel_ip)
        tasks_logger.info(f"Connect to consul at {site_extarnel_ip} "
                          f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master}")
        if feature_toggle_master == "false":
            consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site_extarnel_ip)
            delete_pod(ip=site_extarnel_ip,
                       username=username,
                       password=password,
                       pem_path=pem_path,
                       pod_name="site")
            wait_for(20, "Waiting for api to restart after feature toggle master", tasks_logger)
        if is_service_available(site_extarnel_ip, 3000) and is_service_available(site_extarnel_ip, 16180):
            try:
                tasks_logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true'")
                site_id = hq_session.add_site(site_extarnel_ip)
                tasks_logger.info(f"successfully added site with internal IP {site_extarnel_ip} "
                                  f"and external IP {site_extarnel_ip}")
                return site_id
            except:
                tasks_logger.error(f"Failed to add site with with external IP {site_extarnel_ip} "
                                   f"Attempting to run the automation again")


def delete_site(active_hq_node, hq_session, config):
    hq_session.login()
    sites_id = hq_session.get_sites_id()
    username, pem_path, password, site_extarnel_ip = get_ssh_params(config)
    try:
        remove_site_from_hq = hq_session.remove_site(sites_id)
        tasks_logger.info(f"Delete site from HQ results: {remove_site_from_hq}")
    except:
        tasks_logger.info(f"Nothing to delete result from get_sites_id: {sites_id}")
    disconnect_site = disconnect_site_from_hq(site_extarnel_ip=site_extarnel_ip,
                                              username=password,
                                              password=username,
                                              pem_path=pem_path)
    tasks_logger.debug(f"Attempting connection to {active_hq_node}")
    tasks_logger.info(f"Attemping to disconnect site from HQ")
    delete_pod(ip=active_hq_node,
               username=username,
               password=password,
               pem_path=pem_path,
               pod_name="hq")
    tasks_logger.info(f"Delete site from site results: {disconnect_site}")
    tasks_logger.info("No sites to delete")
