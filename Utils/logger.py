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