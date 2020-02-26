import logging

from socketio_client import verify_recognition_event

task_logger = logging.getLogger(__name__)
task_logger.setLevel(logging.INFO)


def task_wait_for_recog():
    while True:
        try:
            task_logger.info("Started waiting for recognition event")
            recog_event_count = verify_recognition_event(sleep=60)
            if recog_event_count['on_recognition'] <= 0:
                continue
            else:
                return True
        except:
            task_logger.error("Failed to get event from HQ")
