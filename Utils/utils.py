import os
import json


class Utils(object):

    def __init__(self, env):
        with open(os.path.abspath(os.path.join(__file__, '../../config.json')), "rb") as config_file:
            config = json.load(config_file)
        self.env_config = config[env]