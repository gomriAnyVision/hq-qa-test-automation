import logging
import sys
import time

from socketio_client import verify_recognition_event
from vm_management import MachineManagement, VmMgmt, stop_machine, healthy_cluster
from test_end_to_end import HQ_MACHINES, get_sync_status

"""
Test flow
    ensure_all_machines_started
    add camera
    play_stream
    main test LOOP
        stop_machine
        wait untill you start receiving recognition events
        enougth recognition events received start main loop again

"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
handler = logging.StreamHandler(sys.stdout)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(handler)

if __name__ == '__main__':
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(logger)
    # TODO: add function to play stream
    logger.info("----------------------------------------------------------------")
    logger.info("                   STARTING MAIN TEST LOOP                      ")
    logger.info("----------------------------------------------------------------")
    wait_for_cluster = 30
    # TODO: Add site before test starts
    while True:
        for machine, ip in HQ_MACHINES.items():
            healthy_cluster("Healthy", logger)
            stop_machine(machine, wait_for_cluster, logger)
            # healthy_cluster("Healthy", logger)
            HQ_MACHINES[machine] = None
            # sync_status = ""
            # while not sync_status == "synced":
            #     time.sleep(10)
            #     sync_status = get_sync_status()
            #     logger.debug(f"Sync status was: {sync_status} sleeping 10 seconds and trying again")
            # TODO: Ensure we have subjects in HQ watchlist
            start_time = time.time()
            while True:
                logger.info("Started waiting for recognition's")
                if verify_recognition_event(logger, 60):
                    logger.error("Didn't get recognition's trying again")
            end_time = time.time()
            time_delta = start_time - end_time
            logger.info(f"It took {time_delta} seconds to get recognition event")
            result_times.append(time_delta)
            start_machine(machine, wait_for_cluster, logger)
            healthy_cluster("Healthy", logger)


