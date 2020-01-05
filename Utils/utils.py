import os
import json
import argparse
import string
import random


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
        parser.add_argument("--delete_all_subjects", help="True - Delete all subjects from HQ",
                            required=False, default=False)
        parser.add_argument("--run_site_tasks", help="True - Should the script attempt to connect a site and sync it"
                                                     "(feature toggle master etc...)",
                            required=False, default=False)
        parser.add_argument("--connect_to_hq_mongo", help="True - Attempt to connect to the mongo of the HQ",
                            required=False, default=False)
        return parser.parse_args()

    def randomString(self, string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))
