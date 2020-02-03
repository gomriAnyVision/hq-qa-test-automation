import json

from Utils.utils import etc_hosts_insert_mongo_uri, etc_hosts_restore
from pymongo import MongoClient
from urllib.parse import quote_plus
# from automation.devops_automation_infra.plugins.mongodb import MongoDB
# from automation_infra.plugins.base_plugin import plugins
"""
In order to know  which mongo to connect to you must add all mongo 
replicas ips to the the /etc/hosts for example:
<Mongo replica 0 ip>		mongodb.replicaset-0.mongodb-replicaset
<Mongo replica 1 ip>		mongodb.replicaset-1.mongodb-replicaset
<Mongo replica 2 ip>		mongodb.replicaset-2.mongodb-replicaset
"""


class MongoDB(object):
    def __init__(self, mongo_user="", mongo_password="", mongo_host_port_array=""
                , mongo_db="mapi", mongo_auth_db='admin', rs='rs0'):
        uri = f"mongodb://{quote_plus(mongo_user)}:{quote_plus(mongo_password)}@" \
              f"{mongo_host_port_array}/{mongo_db}?authSource={mongo_auth_db}"
        self.client = MongoClient(uri, w=1, journal=True, replicaSet=rs)

    def find(self, db, collection):
        res = db[collection].find({})
        return res

    def get_list_sites(self):
        sites = self.find('db_name', "sites")
        return sites

    def _get_list_sites(self, db):
        self.site_list = []
        res = db.sites.find({})
        for site in res:
            self.site_list.append(site)
        return self.site_list

    def count_subjects(self, db):
        return db.subjects.count()

    def site_sync_status(self):
        db = self._get_db("mapi")
        site_list = self._get_list_sites(db)
        for site in site_list:
            return site['syncStatus']

    def _get_db(self, db):
        return self.client[db]

    def get_sites_id(self):
        db = self._get_db("mapi")
        site_ids = []
        site_list = self._get_list_sites(db)
        for site in site_list:
            site_ids.append(site['_id'])
        return site_ids

def test():
    path = "../config/config_example.json"
    with open(path, 'rb') as conf_path:
        config = json.load(conf_path)
    mongo_service_names = config['mongo']['mongo_service_url'].split(',')
    mongo_for_etc_hosts = f"""{config['mongo']['mongo_zero_ip']}          {mongo_service_names[0]}\n{config['mongo']['mongo_one_ip']}           {mongo_service_names[1]}\n{config['mongo']['mongo_two_ip']}           {mongo_service_names[2]}
    """

    old_state = etc_hosts_insert_mongo_uri(mongo_for_etc_hosts)
    client = MongoDB(mongo_user="root",
                     mongo_password="M2Q1MDUzYjYyOGM4N2JhN2JmYjM1MTMz",
                     mongo_host_port_array=config["mongo"]['mongo_service_url'])
    print(client.get_sites_id())
    etc_hosts_restore(old_state)


# def test_basic(base_config):
#     base_config.hosts.host.MongoDB.connect()