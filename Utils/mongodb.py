from pymongo import MongoClient
from urllib.parse import quote_plus


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
        uri = f"mongodb://{quote_plus(mongo_user)}:{quote_plus(mongo_password)}@{mongo_host_port_array}/{mongo_db}?authSource={mongo_auth_db}"
        self.client = MongoClient(uri, w=1, journal=True, replicaSet=rs)

    def _get_list_sites(self, db):
        self.site_list = []
        res = db.sites.find({})
        for site in res:
            self.site_list.append(site)
        return self.site_list

    def count_subjects(self, db):
        return db.subjects.count()

    def site_sync_status(self, db):
        site_list = self._get_list_sites(db)
        for site in site_list:
            return site['syncStatus'], site['_id']

    def get_db(self, db):
        return self.client[db]

    def get_sites_id(self, db):
        site_ids = []
        site_list = self._get_list_sites(db)
        for site in site_list:
            site_ids.append(site['_id'])
        return site_ids
