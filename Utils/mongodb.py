from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
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

    def find(self, db, collection, query={}):
        res = self.client[db][collection].find(query)
        return res

    def get_list_sites(self):
        sites = self.find("mapi", "sites")
        return sites

    def _get_list_sites(self, db):
        self.site_list = []
        res = db.sites.find()
        for site in res:
            self.site_list.append(site)
        return self.site_list

    def count_subjects(self, db):
        return self.client[db].subjects.count()

    def site_sync_status(self):
        site_list = self._get_list_sites(self.client['mapi'])
        for site in site_list:
            return site['syncStatus']

    def get_sites_id(self):
        site_ids = []
        site_list = self._get_list_sites(self.client['mapi'])
        for site in site_list:
            site_ids.append(site['_id'])
        return site_ids


def test():
    client = MongoDB(mongo_user="root",
                     mongo_password="M2Q1MDUzYjYyOGM4N2JhN2JmYjM1MTMz",
                     mongo_host_port_array="mongodb.replicaset-0.mongodb-replicaset,"
                                           "mongodb.replicaset-1.mongodb-replicaset,"
                                           "mongodb.replicaset-2.mongodb-replicaset")
    for doc in client.get_sites_id():
        assert doc is not None
    assert client.count_subjects("mapi") is not None
    assert client.find("mapi","subjects_groups") is not None


if __name__ == '__main__':
    test()
