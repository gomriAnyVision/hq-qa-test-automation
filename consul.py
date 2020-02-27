import base64
import requests


def consul_set(key, value, ip):
    data = value
    res = requests.put(f"http://{ip}/v1/kv/{key}", data=data,
                       auth=("admin", "Passw0rd123"))
    return res.json()


def consul_get_one(key, ip):
    res = requests.get(f"http://{ip}/v1/kv/{key}",
                       auth=("admin", "Passw0rd123"))
    decoded_res = base64.b64decode(res.json()[0]['Value']).decode("utf-8")
    return decoded_res


def consul_get_with_consistency(logger, ip, key, value):
    try:
        consul_writeable(ip, key, value)
        res = requests.get(f"http://{ip}/v1/kv/{key}", auth=("admin", "Passw0rd123"),params=('consistent'))
        logger.info(f"res status code: {res.status_code} res text: {res.text}")
        assert res.status_code == 200
        if res and res != "":
            return res
    except:
        return False


def consul_writeable(ip, key, data):
    try:
        res = requests.put(f"http://{ip}/v1/kv/{key}", data=data, auth=("admin", "Passw0rd123"))
        print(res)
        assert res.status_code == 200
        return res
    except:
        return False


def consul_get_leader(logger, ip):
    try:
        res = requests.get(f"http://{ip}/consul/v1/status/leader", auth=("admin", "Passw0rd123"))
        assert res.status_code == 200
        if res and res != "":
            logger.info(f"consul_get_leader - result:{res}")
            return True
    except:
        return False


def consul_get_all_nodes_healthcheck(ip, num_servers):
    try:
        server_health = list()
        for i in range(3):
            try:
                res = requests.get(f"http://{ip}/consul/v1/health/node/consul-server-{i}", auth=("admin", "Passw0rd123"))
                if res:
                    resp = res.json()
                    serfHealth = [x for x in resp if x.get('CheckID') == 'serfHealth']
                    if serfHealth:
                        if serfHealth[0].get('Status') == "passing":
                            server_health.append(f'consul-server-{i}')
            except:
                continue
        print(server_health)
        if len(server_health) == num_servers:
            return True
        else:
            return False
    except:
        return False


def verify_all_consul_members_alive(ip):
    try:
        res = requests.get(f"http://{ip}/consul/v1/agent/members", auth=("admin", "Passw0rd123"), params=('consistent'))
        print(res.text, res.status_code)
        # Check that all consul members are alive
        alive_members = len([item.get('Status') for item in res.json() if item and item.get('Status') == 1 and item['Tags'].get('role') == 'consul'])
        print(f"Number of Consul alive Members: {alive_members}")
        return alive_members
    except:
        return 0