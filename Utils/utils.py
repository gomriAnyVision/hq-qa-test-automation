import json
import argparse
import string
import random
import time
import os
import numpy as np

DEFAULT_CONFIG = "config.json"
HOSTS_FILE = "/etc/hosts"


def wait_for(time_to_wait, message, logger):
    logger.info(f"{message} for {time_to_wait} seconds")
    time.sleep(time_to_wait)
    logger.info(f"Finished sleeping {time_to_wait} seconds")


def _etc_mongo_text():
    with open("config.json", "rb") as config :
        mongo_config = json.load(config)['mongo']
    mongo_service_names = mongo_config['mongo_service_name'].split(',')
    mongo_for_etc_hosts = f"{mongo_config['mongo_zero_ip']}  {mongo_service_names[0]} \n" \
                          f"{mongo_config['mongo_one_ip']}   {mongo_service_names[1]} \n" \
                          f"{mongo_config['mongo_two_ip']}   {mongo_service_names[2]}"

    return mongo_for_etc_hosts


def _etc_hosts_write(text):
    with open(HOSTS_FILE, "w") as hosts_file:
        for line in text:
            hosts_file.write(line.decode("utf-8"))


def _etc_hosts_append(text):
    with open(HOSTS_FILE, "ab") as hosts_file:
        try:
            data = text.encode("utf-8")
            hosts_file.write(b"\n" + data)
        except (UnicodeDecodeError, AttributeError):
            hosts_file.write(b"\n" + text)


def _etc_hosts_read():
    with open(HOSTS_FILE, "rb") as hosts_file:
        return hosts_file.readlines()


def etc_hosts_insert_mongo_uri():
    write = _etc_mongo_text()
    state_before_change = _etc_hosts_read()
    if isinstance(write, list):
        for line in write:
            _etc_hosts_append(line)
    else:
        _etc_hosts_append(write)
    return state_before_change


def etc_hosts_restore(history):
    _etc_hosts_write(history)


class Utils(object):
    def __init__(self):
        self.config = ""
        self.args = {}
        with open(DEFAULT_CONFIG, "rb") as config_json:
            self.default_config = json.load(config_json)

    def load_config(self, config_path):
        if not os.path.exists(config_path):
            return
        with open(config_path, "rb") as config_file:
            self.config = json.load(config_file)

    def get_config(self, config_type):
        if not self.config:
            return self.default_config[config_type]
        else:
            return self.config[config_type]

    def get_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--env", help="Which env are you using vm/cloud", required=True)
        parser.add_argument("--add_multiple_subjects", help="Path to the image you want to add a single subject from")
        parser.add_argument("--add_single_subject", help="Path of the zop to run the mass add multiple subjects from")
        parser.add_argument("--delete_all_subjects", help="True - Delete all subjects from HQ")
        parser.add_argument("--run_site_tasks", help="True - Should the script attempt to connect a site and sync it"
                                                     "(feature toggle master etc...)")
        parser.add_argument("--recognition_event", help="True - Run the recognition event test")
        parser.add_argument("--config", help="Path to config file look at example file in config/config_example.json"
                                             "to see what it should contain. config must be in the "
                                             "config/{you're config}.json",
                            default=os.path.abspath(os.path.join(__file__, '../../config/config.json')))
        parser.add_argument("--health_check", help="True - Will run health checks before continuing tests")
        parser.add_argument("--remove_site", help="True - Deletes site")
        parser.add_argument("--stop_nodes", help="True - Stop HQ HA nodes during end to end test")
        self.args = parser.parse_args()
        return parser.parse_args()

    def randomString(self, string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))


def active_ip(machine_list):
    for machine, ip in machine_list.items():
        if ip:
            return ip



def calculate_average(array):
    return np.mean(array)
