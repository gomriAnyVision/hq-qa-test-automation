from pymongo import MongoClient
from urllib.parse import quote_plus

# TODO: connect to mongo return data init


class Mongo(object):
    def connect(self, mongo_user, mongo_password, mongo_host_port_array, mongo_db, mongo_auth_db='admin', rs='rs0'):
        uri = f"mongodb://{quote_plus(mongo_user)}:{quote_plus(mongo_password)}@{mongo_host_port_array}/{mongo_db}?authSource={mongo_auth_db}"
        client = MongoClient(uri, w=1, journal=True, replicaSet=rs)
        if client:
            return client
        else:
            return None

