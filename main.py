import requests
import json
import os
import base64
import time
import logging
import sys
import argparse

DEFAULT_FACE_GROUP = 'ffffffffffffffffffff0000'


class Utils(object):
    def __init__(self, env):
        with open(os.path.abspath(os.path.join(__file__, '../config.json')), "rb") as config_file:
            config = json.load(config_file)
        self.env_config = config[env]

    def logger():
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler("execution.log")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(file_handler)
        return logger


class HQ(object):

    def __init__(self):
        self.request_headers = {
            'authorization': self._login()
        }

    def _login(self):
        res = requests.post('https://hq-api.tls.ai/master/login', data={'username': 'admin', 'password': 'admin'})
        myLogger.info("Successful logged in and got token")
        return res.json()['token']

    def add_subject(self, image):
        with open(image, 'rb') as image_object:
            image_to_upload = image_object.read()
        res = requests.post('https://hq-api.tls.ai/master/subjects/faces-from-image', headers=self.request_headers,
                            files=dict(images=image_to_upload))
        # TODO: Find a better way to extract the subject data from the response
        subject_data = res.json()['data'][0]['results'][0]
        features = subject_data['Features']
        image = subject_data['Image']
        image_qm = subject_data['qm']
        self.request_headers['Content-Type'] = 'application/json; charset=utf-8'
        payload = {
            'name': 'test894179834719823749',
            'description': 'something',
            'useCamerasThreshold': 'false',
            'searchBackwards': 'false',
            'threshold': 0.55,
            'objectType': 'Face',
            'groups': [self.get_subject_group()],
            'data': [{
                'features': features,
                'image': {
                    'image': image,
                    'qm': image_qm}
            }]
        }
        add_subject_res = requests.post('https://hq-api.tls.ai/master/subjects', headers=self.request_headers,
                                        data=json.dumps(payload))
        return add_subject_res

    def add_multiple_subjects(self, file_path):
        with open(file_path, "rb") as zip_file:
            zip_to_import = zip_file.read()
        payload = {"groups": self.get_subject_group()}
        res = requests.post("https://hq-api.tls.ai/master/subjects/bulk", headers=self.request_headers,
                            data=payload,
                            files=dict(zip=zip_to_import))
        return res

    def get_subject_group(self, default=True):
        if default:
            return DEFAULT_FACE_GROUP

    def delete_suspects(self, list_of_subjects):
        self.request_headers["Content-Type"] = "application/json;charset=UTF-8"
        payload = {"subjects": list_of_subjects}
        res = requests.post("https://hq-api.tls.ai/master/subjects/delete", headers=self.request_headers,
                            data=json.dumps(payload))
        return res

    def get_subject_ids(self):
        res = requests.get("https://hq-api.tls.ai/master/subjects", headers=self.request_headers)
        subject_ids = [subject_id['_id'] for subject_id in res.json()['results']]
        return subject_ids

    def add_site(self):
        self.request_headers['Content-Type'] = "application/json; charset=utf-8"
        payload = {
            "siteName": "",
            "address": "",
            "userName": "",
            "password": "",
            "host": f"http://{config['site_internal_ip']}:3000",
            "rmqConnString": f"amqp://{config['site_internal_ip']}:5672",
            "syncServiceUri": f"http://{config['site_internal_ip']}:16180",
            "title": f"site {config['site_internal_ip']}",
            "storageUri": f"https://{config['hq_url']}/r/{config['site_extarnel_ip']}"
        }
        myLogger.info(f"Attempting to add site with payload: {payload}")
        res = requests.post("https://hq-api.tls.ai/master/sites", headers=self.request_headers,
                            data=json.dumps(payload))
        return res

    def consul_set(self, key, value, config):
        data = value
        res = requests.put(f"http://{config['consul_ip']}/v1/kv/{key}", data=data,
                           auth=("admin", "Passw0rd123"))
        return res.json()

    def consul_get_one(self, key, config):
        res = requests.get(f"http://{config['consul_ip']}/v1/kv/{key}",
                           auth=("admin", "Passw0rd123"))
        decoded_res = base64.b64decode(res.json()[0]['Value']).decode("utf-8")
        return decoded_res


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="Which env are you using vm/cloud", nargs=1)
    parser.parse_args()
    config = Utils('cloud').env_config
    myLogger = Utils.logger()
    session = HQ()
    feature_toggle_master_value = session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", config)
    myLogger.info(f"Connect to consul at {config['consul_ip']} "
                  f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master_value}")
    if feature_toggle_master_value == "false":
        session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", config)
        myLogger.info(f"Changed FEATURE_TOGGLE_MASTER to true, sleeping 60 seconds to let "
                      f"API restart properly")
        time.sleep(60)
        myLogger.info("Finished sleeping")
    session.add_site()
    myLogger.info(f"successfully added site with internal IP {config['site_internal_ip']} "
                  f"and external IP {config['site_extarnel_ip']}")
    # session.add_multiple_subjects()
    # session.add_subject()
    # subject_ids = session.get_subject_ids()
    # session.delete_suspects(subject_ids)
