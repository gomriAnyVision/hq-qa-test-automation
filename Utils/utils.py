import os
import json
import argparse


class Utils(object):
    # TODO: config should receive a config file from args and have a default but never parse the path
    def __init__(self):
        with open(os.path.abspath(os.path.join(__file__, '../../config.json')), "rb") as config_file:
            config = json.load(config_file)
            self.env_config = config

    def get_config(self, config_type):
        return self.env_config[config_type]

    def get_args(self):
        parser = argparse.ArgumentParser()
        # TODO: Add default config path to the --env arg
        parser.add_argument("--env", help="Which env are you using vm/cloud")
        parser.add_argument("--add_multiple_subjects", help="Path to the image you want to add a single subject from",
                            required=False, default=False)
        parser.add_argument("--add_single_subject", help="Path of the zop to run the mass add multiple subjects from",
                            required=False, default=False)
        return parser.parse_args()
