# import logging
# import sys
#
#
# def logger():
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     file_handler = logging.FileHandler("execution.log")
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     logger.addHandler(file_handler)
#     return  logger
#
