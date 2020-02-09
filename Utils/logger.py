import logging
import os
import sys


class Logger(object):
    # TODO: Logger shouldn't create a logger but only add the basic settings the logger,
    #  each file should create it's own log
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO or os.environ.get("DEBUGLEVEL"))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("execution.log")
        handler = logging.StreamHandler(sys.stdout)
        file_handler.setFormatter(formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

def test():
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG or os.environ.get("LOGLEVEL"))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler("execution.log")
    file_handler.setFormatter(formatter)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(handler)
    logger.debug("s")
