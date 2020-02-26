import logging
import sys
import time
from pprint import pformat

from Utils.utils import get_default_config, Utils, calculate_average
from tasks import task_wait_for_recog
from vm_management import MachineManagement, VmMgmt, stop_machine, healthy_cluster, start_machine

HQ_MACHINES = get_default_config()['hq_machines']
SYNC_STATUS = None
RESULT_TIMES = []
WAIT_FOR_CLUSTER = 0
ITERATION_NUMBER = 1
AVERAGE_TIME = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
file_handler.setFormatter(formatter)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(handler)


def alive_hq_node_ip():
    global HQ_MACHINES
    for machine, ip in HQ_MACHINES.items():
        if ip:
            return ip


if __name__ == '__main__':
    Utils = Utils()
    args = Utils.get_args()
    Utils.load_config(args.config)
    logger.info(f"Starting tests with {args}")
    env_config = Utils.get_config(args.env)
    logger.info(f"Received config: {pformat(env_config)}")
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(logger)
    healthy_cluster("Healthy", logger, alive_hq_node_ip(), minimum_nodes_running=3)
    # TODO: add function to play stream
    # TODO: Add site before test starts
    # TODO: Ensure we have subjects in HQ watchlist
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    while True:
        for machine, ip in HQ_MACHINES.items():
            stop_node = time.time()
            logger.info(f"Stopping Machine:{machine} IP:{ip} ")
            stop_machine(machine, WAIT_FOR_CLUSTER, logger)
            HQ_MACHINES[machine] = None
            task_wait_for_recog()
            received_recog = time.time()
            time_delta = received_recog - stop_node
            logger.info(f"It took {time_delta} seconds to get recognition event after stopping ndoe")
            RESULT_TIMES.append(time_delta)
            start_machine(machine, WAIT_FOR_CLUSTER, logger)
            healthy_cluster("Healthy", logger, alive_hq_node_ip(), minimum_nodes_running=3)
            AVERAGE_TIME = calculate_average(RESULT_TIMES)
            HQ_MACHINES[machine] = ip
            logger.info(f"average time from stopping node to receviing recognition from already connected site: "
                        f"{AVERAGE_TIME}")
            ITERATION_NUMBER += 1
            logger.info(f"Number of iterations: {ITERATION_NUMBER}")


