import os
import json
import argparse
import string
import random
import time

DEFAULT_CONFIG = "config/config.json"


def wait_for(time_to_wait, message, logger):
    logger.info(f"{message} for {time_to_wait}")
    time.sleep(time_to_wait)
    logger.info(f"Finished sleeping {time_to_wait} seconds")


class Utils(object):
    # TODO: config should receive a config file from args and have a default but never parse the path
    def __init__(self):
        self.config = ""
        with open(os.path.abspath(os.path.join(DEFAULT_CONFIG)), "rb") as config_json:
            self.default_config = json.load(config_json)

    def set_config(self, config_path):
        if not os.path.exists(config_path):
            # TODO: support default config file
            return
        with open(config_path, "rb") as config_file:
            self.config = json.load(config_file)
            return self.config

    def get_config(self, config_type):
        if not self.config:
            return self.default_config[config_type]
        else:
            return self.config[config_type]

    def get_args(self):
        parser = argparse.ArgumentParser()
        # TODO: Add default config path to the --env arg
        parser.add_argument("--env", help="Which env are you using vm/cloud", required=True)
        parser.add_argument("--add_multiple_subjects", help="Path to the image you want to add a single subject from")
        parser.add_argument("--add_single_subject", help="Path of the zop to run the mass add multiple subjects from")
        parser.add_argument("--delete_all_subjects", help="True - Delete all subjects from HQ")
        parser.add_argument("--run_site_tasks", help="True - Should the script attempt to connect a site and sync it"
                                                     "(feature toggle master etc...)")
        parser.add_argument("--connect_to_hq_mongo", help="True - Attempt to connect to the mongo of the HQ")
        parser.add_argument("--recognition_event", help="True - Run the recognition event test")
        parser.add_argument("--config", help="Path to config file look at example file in config/config_example.json"
                                             "to see what it should contain. config must be in the "
                                             "config/{you're config}.json",
                            default=os.path.abspath(os.path.join(__file__, '../../config/config.json')))
        parser.add_argument("--remove_site", help="True - Deletes site")
        return parser.parse_args()

    def randomString(self, string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))

