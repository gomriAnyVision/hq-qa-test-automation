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


def delete_site(active_hq_node, hq_session, config):
    sites_id = hq_session.get_sites_id()
    username, pem_path, password = config['vm'][0]['ssh'].values()
    site_extarnel_ip = config['vm'][0]['site_extarnel_ip']
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
