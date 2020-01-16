import threading
import requests
import json
import base64
import time
from pprint import pformat

from Utils.mongodb import MongoDB
from Utils.logger import Logger
from Utils.utils import Utils
from ssh import disconnect_site_from_hq
from socketio_client import verify_mass_import_event, verify_recognition_event
from site_api import play_forensic

DEFAULT_FACE_GROUP = 'ffffffffffffffffffff0000'


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
            'name': Utils.randomString(),
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

    def get_subject_ids(self, limit=500):
        test_logger.info(f"Get the first {limit} Id's of subjects")
        res = requests.get("https://hq-api.tls.ai/master/subjects", headers=self.request_headers,
                           params={'limit': limit})
        subject_ids = [subject_id['_id'] for subject_id in res.json()['results']]
        test_logger.info(f"Got id's of {len(subject_ids)}")
        return subject_ids

    def remove_site(self, site_id):
        res = requests.delete(f"https://hq-api.tls.ai/master/sites/{site_id}", headers=self.request_headers)
        return res.json()

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
        test_logger.info(f"Attempting to add site with payload: {pformat(payload)}")
        res = requests.post("https://hq-api.tls.ai/master/sites", headers=self.request_headers,
                            data=json.dumps(payload))
        assert res.status_code == 200
        return res.json()['_id']

    def consul_set(self, key, value, config):
        data = value
        res = requests.put(f"http://{config['site_consul_ip']}/v1/kv/{key}", data=data,
                           auth=("admin", "Passw0rd123"))
        return res.json()

    def consul_get_one(self, key, config):
        res = requests.get(f"http://{config['site_consul_ip']}/v1/kv/{key}",
                           auth=("admin", "Passw0rd123"))
        decoded_res = base64.b64decode(res.json()[0]['Value']).decode("utf-8")
        return decoded_res


if __name__ == '__main__':
    # TODO: Run test forever on or until set time
    Utils = Utils()
    Logger = Logger()
    args = Utils.get_args()
    config = Utils.set_config(args.config)
    ssh_config = Utils.get_config('ssh')
    mongo_config = Utils.get_config('mongo')
    env_config = Utils.get_config(args.env)
    test_logger = Logger.get_logger()
    # TODO: log the ip of the mongo your connecting to
    test_logger.info(f"Attempting to connect to Mongo HQ using: {pformat(mongo_config)}")
    hq_mongo_client = MongoDB(mongo_password=mongo_config['hq_pass'],
                              mongo_user=mongo_config['hq_user'],
                              mongo_host_port_array=mongo_config['mongo_service_name'])
    test_logger.info("results of connection to mongo:{}".format(hq_mongo_client))
    mapi = hq_mongo_client.get_db('mapi')
    site_ids = hq_mongo_client.get_sites_id(mapi)
    test_logger.info(f"Found the following site ids in the HQ mongo:{pformat(site_ids)}")
    sites_sync_status = hq_mongo_client.site_sync_status(mapi)
    test_logger.info(f"Sites sync status is: {pformat(sites_sync_status)}")
    test_logger.info(f"Initiated config with: {pformat(env_config)}")
    test_logger.info(f"Received the following args: {args}")
    session = HQ()
    if args.run_site_tasks:
        for site in env_config:
            feature_toggle_master_value = session.consul_get_one("api-env/FEATURE_TOGGLE_MASTER", site)
            test_logger.info(f"Connect to consul at {site['site_consul_ip']} "
                             f"and get FEATURE_TOGGLE_MASTER value = {feature_toggle_master_value}")
            if feature_toggle_master_value == "false":
                session.consul_set("api-env/FEATURE_TOGGLE_MASTER", "true", site)
                test_logger.info(f"Changed FEATURE_TOGGLE_MASTER = 'true', sleeping 60 seconds to let "
                                 f"API restart properly")
                time.sleep(60)
                test_logger.info("Finished sleeping")
            site_id = session.add_site(site)
            test_logger.info(f"successfully added site with internal IP {site['site_internal_ip']} "
                             f"and external IP {site['site_extarnel_ip']}")
            # TODO: Add adds to function to control which test should run or consider intergrating pytest
    if args.add_multiple_subjects:
        verify_mass_import_event(session, args, test_logger, sleep=5)
    if args.add_single_subject:
        session.add_subject(args.add_single_subject)
    if args.delete_all_subjects:
        subject_ids = session.get_subject_ids()
        session.delete_suspects(subject_ids)
    if args.remove_site:
        for site in site_ids:
            test_logger.info(f"Attempting to delete site: {site}")
            remove_site_from_hq = session.remove_site(site)
            disconnect_site = disconnect_site_from_hq(env_config, ssh_config)
            test_logger.info(f"Delete site from HQ results: {pformat(remove_site_from_hq)}")
            test_logger.info(f"Delete site from site results: {disconnect_site}")
    # TODO: Verify this test works once the sites are able to sync
    if args.recognition_event:
        play_forensic(env_config)
        verify_recognition_event()

