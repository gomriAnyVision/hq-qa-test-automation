import json
import requests


def _upload_video(config):
    files = {"files": open("./assets/subject_recognition.mp4", "rb")}
    res = requests.post(f"http://{config[0]['site_extarnel_ip']}:3000/video-sources/video/file", files=files)
    return res.json()["data"][0]


def play_forensic(config, threshold=0.05):
    forenisc_file_path = _upload_video(config)
    with open("./forensic_template.json", "rb") as payload_template:
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        payload = json.load(payload_template)
        payload["cameras"][0]["setting_threshold"] = threshold
        payload['cameras'][0]['video_urls'][0] = forenisc_file_path
        payload['files']["videoUrls"][0] = forenisc_file_path
        res = requests.post(f"http://{config[0]['site_extarnel_ip']}:3000/video-sources/video", headers=headers,
                            data=json.dumps(payload))
        assert 200
        return res


def is_api_available(ip):
    result = None
    while result is None:
        try:
            result = requests.get(f"http://{ip}:3000", timeout=5)
            print(result.text)
            return result
        except:
            print(result)