import os
import json


class Utils(object):
    #TODO: config should recevie a config file from args and have a default but never parse the path
    def __init__(self, env):
        with open(os.path.abspath(os.path.join(__file__, '../../config.json')), "rb") as config_file:
            config = json.load(config_file)
        self.env_config = config[env]

    def get_config(self):
        return self.env_config