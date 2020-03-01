from pprint import pformat
import time

from Utils.logger import myLogger
from Utils.utils import Utils, active_ip, calculate_average
from hq import HQ
from vm_management import  MachineManagement, healthy_cluster, VmMgmt, start_machine, randomize_stop_reboot_method
from tasks import delete_site, wait_for_add_site

RESULT_TIMES = []
ITERATION_NUMBER = 0
WAIT_FOR_CLUSTER = 0

if __name__ == '__main__':
    utils = Utils()
    logger = myLogger(__name__)
    args = utils.get_args()
    utils.load_config(args.config)
    logger.info(f"Starting tests with {args}")
    env_config = utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    hq_machines = utils.config['hq_machines']
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(logger)
    active_hq_node = active_ip(hq_machines)
    healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
    hq_session = HQ()
    delete_site(active_hq_node, hq_session, utils.config)
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    while True:
        for machine, ip in hq_machines.items():
            stop_node = time.time()
            logger.info(f"Stopping Machine:{machine} IP:{ip} ")
            randomize_stop_reboot_method(ip, machine)
            hq_machines[machine] = None
            # Attempt to add site
            site_id = wait_for_add_site(hq_session, utils.config)
            added_site = time.time()
            time_delta = added_site - stop_node
            logger.info(f"It took {time_delta} seconds to ADD SITE after stopping node")
            RESULT_TIMES.append(time_delta)
            start_machine(machine, WAIT_FOR_CLUSTER)
            logger.info(f"STARTING CLEAN UP")
            active_hq_node = active_ip(hq_machines)
            healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
            AVERAGE_TIME = calculate_average(RESULT_TIMES)
            hq_machines[machine] = ip
            active_hq_node = active_ip(hq_machines)
            hq_session.login()
            delete_site(active_hq_node, hq_session, utils.config)
            logger.info("FINISHED CLEAN UP")
            logger.info(f"average time from stopping node to adding site: {AVERAGE_TIME}")
            ITERATION_NUMBER += 1
            logger.info(f"Number of iterations: {ITERATION_NUMBER}")

