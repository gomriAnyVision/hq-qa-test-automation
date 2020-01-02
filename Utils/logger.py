import logging
import sys


class Logger(object):
    # TODO: Logger shouldn't create a logger but only add the basic settings the logger,
    #  each file should create it's own log
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("execution.log")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger
