import time
from pprint import pformat

import requests
import json
import base64

from Utils.logger import myLogger
from Utils.utils import Utils

DEFAULT_FACE_GROUP = 'ffffffffffffffffffff0000'

logger = myLogger(__name__)


class HQ(object):
    def __init__(self):
        self.request_headers = {}

    def get_request_headers(self):
        return self.request_headers if self.request_headers else None

    def login(self):
        try:
            res = requests.post('https://hq-api.tls.ai/master/login',
                                data={'username': 'admin', 'password': 'admin'})
            time.sleep(1)
            logger.info(f"Response: {res}, response text {res.status_code}")
            assert res.status_code == 200
            self.request_headers['authorization'] = res.json()['token']
            return True
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed to login error: {err}")

    def add_subject(self, image="assets/subject.jpeg"):
        with open(image, 'rb') as image_object:
            image_to_upload = image_object.read()
        self.request_headers['Content-Type'] = 'image/jpeg'
        res = requests.post('https://hq-api.tls.ai/master/subjects/faces-from-image',
                            headers=self.request_headers, files=dict(images=image_to_upload))
        subject_data = res.json()['data'][0]['results'][0]
        features = subject_data['Features']
        image = subject_data['Image']
        image_qm = subject_data['qm']
        self.request_headers['Content-Type'] = 'application/json; charset=utf-8'
        payload = {
            'name': Utils().randomString(),
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
        res = requests.get("https://hq-api.tls.ai/master/subjects", headers=self.request_headers,
                           params={'limit': limit})
        subject_ids = [subject_id['_id'] for subject_id in res.json()['results']]
        return subject_ids

    def remove_site(self, site_id):
        if isinstance(site_id, list):
            print("remove site in case of list this currently only support the first index of list")
            res = requests.delete(f"https://hq-api.tls.ai/master/sites/{site_id[0]}", headers=self.request_headers)
            return res.json()
        if len(site_id) > 0:
            res = requests.delete(f"https://hq-api.tls.ai/master/sites/{site_id}", headers=self.request_headers)
            return res.json()
        else:
            return

    def add_site(self, ip):
        self.request_headers['Content-Type'] = "application/json; charset=utf-8"
        payload = {
            "host": f"http://{ip}:3000",
            "rmqConnString": f"amqp://{ip}:5672",
            "syncServiceUri": f"http://{ip}:16180",
            "title": f"site {ip}",
            "storageUri": f"https://hq.tls.ai/r/{ip}"
        }
        logger.debug(f"Add site request payload: {pformat(payload)}")
        res = requests.post("https://hq-api.tls.ai/master/sites", headers=self.request_headers,
                            data=json.dumps(payload))
        logger.info(f"response status code: {res.status_code}, text: {res.text}")
        logger.debug(f"Res add site: {res}")
        return res.json()['_id']

    def get_sites(self):
        """
        positions 0 - sites_ids: all the sites which are connected to the HQ's ids
        positions 1 - site_sync_status: all the the sites which are connected to the HQ's sync status'
        """
        try:
            res = requests.get("https://hq-api.tls.ai/master/sites?withCameras=true", headers=self.request_headers)
            if res.json() and res.json() != []:
                sites_ids = [site_id['_id'] for site_id in res.json()]
                site_sync_status = [sync_status["syncStatus"].get('status') for sync_status in res.json()]
                if site_sync_status and sites_ids:
                    return sites_ids, site_sync_status
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed to get site error: {err}")

    def get_sync_status(self):
        if self.get_sites():
            _, result = self.get_sites()
            if result:
                return result[0]

    def get_sites_id(self):
        if self.get_sites():
            result, _ = self.get_sites()
            if result:
                return result

if __name__ == "__main__":
    hq_session = HQ()
    subject_ids = hq_session.get_subject_ids(1000)
    hq_session.delete_suspects(subject_ids)
