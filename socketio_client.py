import socketio
import threading
import time

sio = socketio.Client()
HOST = "https://hq-api.tls.ai:443/"

event_count = {}
subject_imported = 10


def _connect_to_socket_and_wait():
    sio.connect(HOST)
    try:
        sio.wait()
    except:
        pass


def _disconnect():
    sio.eio.disconnect()
    print("Closed socket")


@sio.on("connect")
def on_connect():
    print(f"connected to socket at {HOST}")


@sio.on("mass_import_events_completed")
def on_mass_mass_import_completed(*args):
    global subject_imported
    global event_count
    event_count['mass_import_events_completed'] = 1
    try:
        assert f"{subject_imported} were new and inserted to the database" in args[0]
    except AssertionError:
        print(f"Expected {subject_imported} to be imported but only {args[0]}")


@sio.on("new_recognition")
def on_recognition(*args):
    event_count["on_recognition"] = 1
    print(*args)


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
    logger.info(f"Expected {subject_imported} inserted from mass import ")
    session.add_multiple_subjects(args.add_multiple_subjects)
    time.sleep(sleep)
    try:
        assert event_count["mass_import_events_completed"] > 0
    except AssertionError:
        logger.error(f"Failed to receive mass import event {HOST}")
    _disconnect()
    socket_thread.join()


def verify_recognition_event(logger, sleep=5):
    """
    Executes the add single subject task and verify the subject is created in the site by verify an event
    is received when the subject is recognized

    :parameter event_count: a dict which holds counter for each event received
    :param logger: logger to log the results
    :param sleep: how long ot wait for the recognition event
    """
    socket_thread = threading.Thread(target=_connect_to_socket_and_wait)
    socket_thread.setDaemon(True)
    socket_thread.start()
    logger.info("Waiting for recognition event")
    time.sleep(sleep)
    try:
        assert event_count["on_recognition"] > 0
    except AssertionError:
        logger.error(f"Failed to receive recognition event {HOST}")
    _disconnect()
    socket_thread.join()