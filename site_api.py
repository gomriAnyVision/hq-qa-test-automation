import json
import time

import requests

from Utils.logger import myLogger

logger = myLogger(__name__)

def _upload_video(ip):
    files = {"files": open("./assets/subject_recognition.mp4", "rb")}
    res = requests.post(f"http://{ip}:3000/video-sources/video/file", files=files)
    return res.json()["data"][0]


def play_forensic(ip, threshold=0.05):
    forenisc_file_path = _upload_video(ip)
    with open("./forensic_template.json", "rb") as payload_template:
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        payload = json.load(payload_template)
        payload["cameras"][0]["setting_threshold"] = threshold
        payload['cameras'][0]['video_urls'][0] = forenisc_file_path
        payload['files']["videoUrls"][0] = forenisc_file_path
        res = requests.post(f"http://{ip}:3000/video-sources/video", headers=headers,
                            data=json.dumps(payload))
        assert 200
        return res


def is_service_available(ip, port):
    result = None
    while result is None:
        try:
            result = requests.get(f"http://{ip}:{port}", timeout=5)
            logger.info(f"res from {ip}:{port} - {result.text}")
            return result
        except:
            logger.error(f"Failed to get healthy status from from {ip}:{port} "
                         f"Result - {result} sleeping 2 sceonds and trying again")
            time.sleep(2)

