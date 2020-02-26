import logging
import sys

import socketio
from socketio.exceptions import ConnectionError
import threading
import time

sio = socketio.Client()

HOST = "https://hq-api.tls.ai:443/"
SUBJECTS_IMPORTED = 10

event_count = {}

socket_logger = logging.getLogger("socket_logger")
socket_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("execution.log")
file_handler.setFormatter(formatter)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
socket_logger.addHandler(file_handler)
socket_logger.addHandler(handler)


def _connect_to_socket_and_wait():
    sio.connect(HOST)
    try:
        sio.wait()
    except socketio.exceptions.ConnectionError:
        pass


def _disconnect():
    sio.eio.disconnect()
    print("Closed socket")


@sio.on("connect")
def on_connect():
    print(f"connected to socket at {HOST}")


@sio.on("mass_import_events_completed")
def on_mass_mass_import_completed(*args):
    global SUBJECTS_IMPORTED
    global event_count
    event_count['mass_import_events_completed'] = 1
    try:
        assert f"{SUBJECTS_IMPORTED} were new and inserted to the database" in args[0]
    except AssertionError:
        print(f"Expected {SUBJECTS_IMPORTED} to be imported but only {args[0]}")


@sio.on("new_recognition")
def on_recognition(*args):
    socket_logger.debug(f"new_recognition event: {args}")
    event_count["on_recognition"] = 1


@sio.on("new_subject_request")
def on_new_subject_request(*args):
    print(args)


def verify_mass_import_event(session, args, logger, sleep=5):
    """
    This executes the mass import task on the HQ and verify the correct event is sent to the socket

    :parameter event_count: a dict which holds counter for each event received
    :param session: The HQ session to use for the mass import
    :param args: The config.args used for the mass import in this case the path to Mass import file
    :param logger: The logger to use to log the results
    :param sleep: How long to keep the socket open and waiting for an event from the hq-api
    """

    socket_thread = threading.Thread(target=_connect_to_socket_and_wait)
    socket_thread.setDaemon(True)
    socket_thread.start()
    logger.info(f"Expecting {SUBJECTS_IMPORTED} subjects to be inserted via mass import ")
    session.add_multiple_subjects(args.add_multiple_subjects)
    time.sleep(sleep)
    try:
        assert event_count["mass_import_events_completed"] > 0
    except AssertionError:
        logger.error(f"Failed to receive mass import event {HOST}")
    _disconnect()
    socket_thread.join()

# TODO: Fix bug ValueError: Client is not in a disconnected state
def verify_recognition_event(sleep=20):
    """
    Executes the add single subject task and verify the subject is created in the site by verify an event
    is received when the subject is recognized

    :parameter event_count: a dict which holds counter for each event received
    :param logger: logger to log the results
    :param sleep: how long ot wait for the recognition event
    """
    socket_logger.info("Connecting to HQ dashboard socketio waiting for recognition event")
    _disconnect()
    socket_thread = threading.Thread(target=_connect_to_socket_and_wait)
    try:
        socket_thread.setDaemon(True)
        socket_thread.start()
        socket_logger.info("Waiting for recognition event")
        time.sleep(sleep)
        assert event_count["on_recognition"] > 0
        print(event_count)
        _disconnect()
        return event_count
    except AssertionError:
        socket_logger.error(f"Failed to receive recognition event {HOST}")
    _disconnect()
    socket_thread.join()
