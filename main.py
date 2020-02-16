import requests
import json
import base64

from Utils.utils import Utils


DEFAULT_FACE_GROUP = 'ffffffffffffffffffff0000'


class HQ(object):
    # TODO: Think about soluations to checking request failers
    def __init__(self):
        self.request_headers = {
            'authorization': self._login()
        }

    def _login(self):
        for attempts in range(1, 10):
            try:
                res = requests.post('https://hq-api.tls.ai/master/login',
                                    data={'username': 'admin', 'password': 'admin'})
                assert res.status_code == 200
                return res.json()['token']
            except:
                print(res.status_code, res.json() if res.json() else "")
                print("Failed to login")

    def add_subject(self, image="assets/subject.jpeg"):
        with open(image, 'rb') as image_object:
            image_to_upload = image_object.read()
        self.request_headers['Content-Type'] = 'image/jpeg'
        res = requests.post('https://hq-api.tls.ai/master/subjects/faces-from-image',
                            headers=self.request_headers, files=dict(images=image_to_upload))
        # TODO: Find a better way to extract the subject data from the response
        print(res)
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

    def add_site(self, config):
        self.request_headers['Content-Type'] = "application/json; charset=utf-8"
        payload = {
            "host": f"http://{config['site_internal_ip']}:3000",
            "rmqConnString": f"amqp://{config['site_internal_ip']}:5672",
            "syncServiceUri": f"http://{config['site_internal_ip']}:16180",
            "title": f"site {config['site_internal_ip']}",
            "storageUri": f"https://{config['hq_url']}/r/{config['site_extarnel_ip']}"
        }
        res = requests.post("https://hq-api.tls.ai/master/sites", headers=self.request_headers,
                            data=json.dumps(payload))
        print(res)
        return res.json()['_id']

    def get_sites(self):
        """
        positions 0 - sites_ids: all the sites which are connected to the HQ's ids
        positions 1 - site_sync_status: all the the sites which are connected to the HQ's sync status'
        """
        res = requests.get("https://hq-api.tls.ai/master/sites?withCameras=true", headers=self.request_headers)
        if res.json() and res.json() != []:
            sites_ids = [site_id['_id'] for site_id in res.json()]
            site_sync_status = [sync_status["syncStatus"].get('status') for sync_status in res.json()]
            if site_sync_status and sites_ids:
                return sites_ids, site_sync_status

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


if __name__ == "__main__":
    hq_session = HQ()
    subject_ids = hq_session.get_subject_ids(1000)
    hq_session.delete_suspects(subject_ids)
