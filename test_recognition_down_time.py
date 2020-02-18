import logging
import sys

from vm_management import MachineManagement, VmMgmt, stop_machine
from test_end_to_end import HQ_MACHINES

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

recognition_down_time_logger = logging.getLogger(__name__)
recognition_down_time_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
handler = logging.StreamHandler(sys.stdout)
file_handler.setFormatter(formatter)
recognition_down_time_logger.addHandler(file_handler)
recognition_down_time_logger.addHandler(handler)

if __name__ == '__main__':
    machine_mgmt = MachineManagement(VmMgmt())
    machine_mgmt.ensure_all_machines_started(recognition_down_time_logger)
    play_stream()
    recognition_down_time_logger.info("----------------------------------------------------------------")
    recognition_down_time_logger.info("                   STARTING MAIN TEST LOOP                      ")
    recognition_down_time_logger.info("----------------------------------------------------------------")
    wait_for_cluster = 30
    while True:
        for machine, ip in HQ_MACHINES.items():
            stop_machine(machine, wait_for_cluster, recognition_down_time_logger)