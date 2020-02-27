import datetime
import logging
import sys


loggers = {}


def myLogger(name):
    global loggers

    if loggers.get(name):
        return loggers.get(name)
    else:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        now = datetime.datetime.now()
        handler = logging.FileHandler(
            'execution'
            + now.strftime("%Y-%m-%d")
            + '.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')
        sys_out_handler = logging.StreamHandler(sys.stdout)
        sys_out_handler.setFormatter(formatter)
        handler.setFormatter(formatter)
        logger.addHandler(sys_out_handler)
        logger.addHandler(handler)
        loggers[name] = logger

        return logger

# class Logger(object):
#     # TODO: Logger shouldn't create a logger but only add the basic settings the logger,
#     #  each file should create it's own log
#     def __init__(self):
#         self.logger = logging.getLogger()
#         self.logger.setLevel(logging.INFO or os.environ.get("DEBUGLEVEL"))
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(func)s - %(lineno)s - %(levelname)s - %(message)s')
#         file_handler = logging.FileHandler("execution.log")
#         handler = logging.StreamHandler(sys.stdout)
#         file_handler.setFormatter(formatter)
#         handler.setFormatter(formatter)
#         self.logger.addHandler(handler)
#         self.logger.addHandler(file_handler)
#
#     def get_logger(self):
#         return self.logger
