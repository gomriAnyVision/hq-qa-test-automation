import logging
import sys
import time

from vm_management import MachineManagement, VmMgmt, stop_machine
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

recog_down_time_logger = logging.getLogger(__name__)
recog_down_time_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
handler = logging.StreamHandler(sys.stdout)
file_handler.setFormatter(formatter)
recog_down_time_logger.addHandler(file_handler)
recog_down_time_logger.addHandler(handler)

if __name__ == '__main__':
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(recog_down_time_logger)
    play_stream()
    recog_down_time_logger.info("----------------------------------------------------------------")
    recog_down_time_logger.info("                   STARTING MAIN TEST LOOP                      ")
    recog_down_time_logger.info("----------------------------------------------------------------")
    wait_for_cluster = 30
    # TODO: Add site befor test starts
    while True:
        for machine, ip in HQ_MACHINES.items():
            stop_machine(machine, wait_for_cluster, recog_down_time_logger)
            HQ_MACHINES[machine] = None
            sync_status = ""
            while not sync_status == "synced":
                time.sleep(10)
                sync_status = get_sync_status()
                recog_down_time_logger.debug(f"Sync status was: {sync_status} sleeping 10 seconds and trying again")
                # TODO: Ensure we have subjects in HQ watchlist
