import requests
import json
import base64
import time
import uuid

from Utils.mongodb import Mongo
from Utils.logger import Logger
from Utils.utils import Utils
from vm_management import VmManager


DEFAULT_FACE_GROUP = 'ffffffffffffffffffff0000'



# def test_HQ_HA():
#     while True:
#         for vm in vm_list:
#             while vm_count() != 3:
#                 test_logger.info("Sleeping 10 seconds waiting for 3rd vm to be active")
#                 sleep(10)
#             add_site()
#             add_subject()
#             result = test_subject_appears_in_site()
#             if result:
#                 test_logger.info(f"Subject appear both on site and HQ")
#             else:
#                 test_logger.error(f"Subject failed to get to site IMPORT LOG DATA}")
#             remove_site()
#             start_vm(vm_name)


class HQ(object):
    # TODO: Think about soluations to checking request failers
    def __init__(self):
        self.request_headers = {
            'authorization': self._login()
        }

    def _login(self):
        res = requests.post('https://hq-api.tls.ai/master/login', data={'username': 'admin', 'password': 'admin'})
        test_logger.info("Successful logged in and got token")
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
            'name': uuid.uuid1(),
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
                            data=payload, files=dict(zip=zip_to_import))
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

    def add_site(self, config):
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
        test_logger.info(f"Attempting to add site with payload: {payload}")
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
    # TODO: Run test forever on or until set time
    Mongo = Mongo()
    Utils = Utils()
    Logger = Logger()
    args = Utils.get_args()
    env_config = Utils.get_config(args.env)
    test_logger = Logger.get_logger()
    vm_manager = VmManager()
    test_logger.info(f"Attempting to Mongo on {env_config['site_internal_ip']}")
    mongo_client = Mongo.connect("root",)
    test_logger.info(f"results of connection to mongo:{mongo_client}")
    test_logger.info(f"Initiated config with: {env_config}")
    test_logger.info(f"Received the following args: {args}")
    session = HQ()
    feature_toggle_master_value = session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", env_config)
    test_logger.info(f"Connect to consul at {env_config['consul_ip']} "
                     f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master_value}")
    if feature_toggle_master_value == "false":
        session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", env_config)
        test_logger.info(f"Changed FEATURE_TOGGLE_MASTER to true, sleeping 60 seconds to let "
                         f"API restart properly")
        time.sleep(60)
        test_logger.info("Finished sleeping")
    session.add_site(env_config)
    test_logger.info(f"successfully added site with internal IP {env_config['site_internal_ip']} "
                     f"and external IP {env_config['site_extarnel_ip']}")
    # TODO: Add adds to function to control which test should run or consider intergrating pytest
    if args.add_multiple_subjects:
        session.add_multiple_subjects(args.add_multiple_subjects)
    if args.add_sinagle_subject:
        session.add_subject(args.add_sinagle_subject)
    subject_ids = session.get_subject_ids()
    # session.delete_suspects(subject_ids)
