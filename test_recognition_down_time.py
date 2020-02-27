import logging
import sys
import time
from pprint import pformat

from Utils.logger import myLogger
from Utils.utils import active_ip, Utils, calculate_average
from tasks import wait_for_recog
from vm_management import MachineManagement, VmMgmt, stop_machine, healthy_cluster, start_machine

SYNC_STATUS = None
RESULT_TIMES = []
WAIT_FOR_CLUSTER = 0
ITERATION_NUMBER = 1
AVERAGE_TIME = 0



if __name__ == '__main__':
    utils = Utils()
    args = utils.get_args()
    logger = myLogger(__name__)
    utils.load_config(args.config)
    logger.info(f"Starting tests with {args}")
    env_config = utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    hq_machines = utils.config['hq_machines']
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(logger)
    active_hq_node = active_ip(hq_machines)
    healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
    # TODO: add function to play stream
    # TODO: Add site before test starts
    # TODO: Ensure we have subjects in HQ watchlist
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    while True:
        for machine, ip in hq_machines.items():
            stop_node = time.time()
            logger.info(f"Stopping Machine:{machine} IP:{ip} ")
            stop_machine(machine, WAIT_FOR_CLUSTER, logger)
            hq_machines[machine] = None
            wait_for_recog()
            received_recog = time.time()
            time_delta = received_recog - stop_node
            logger.info(f"It took {time_delta} seconds to get recognition event after stopping ndoe")
            RESULT_TIMES.append(time_delta)
            start_machine(machine, WAIT_FOR_CLUSTER, logger)
            active_hq_node = active_ip(hq_machines)
            healthy_cluster("Healthy", logger, active_hq_node, minimum_nodes_running=3)
            AVERAGE_TIME = calculate_average(RESULT_TIMES)
            hq_machines[machine] = ip
            logger.info(f"average time from stopping node to receviing recognition from already connected site: "
                        f"{AVERAGE_TIME}")
            ITERATION_NUMBER += 1
            logger.info(f"Number of iterations: {ITERATION_NUMBER}")


