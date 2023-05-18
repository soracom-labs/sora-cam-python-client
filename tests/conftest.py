#!/usr/bin/env python3


import os
import logging
import pathlib
import shutil
import filetype
import glob
import tempfile
import pytest
from dotenv import load_dotenv

from soracam.soracam_api import SoraCamClient as sc

load_dotenv()

_VIDEO_DURATION = os.environ.get('VIDEO_DURATION', 10000)
_VIDEO_OFFSET = os.environ.get('VIDEO_OFFSET', 1000)
_DEVICE_ID = os.environ.get('DEVICE_ID', '')

_DEBUG = os.environ.get('DEBUG', 'True').lower() in ['true', '1']

# log settings
FORMAT = '%(levelname)s %(asctime)s \
    %(funcName)s %(filename)s %(lineno)d %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
if _DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


@pytest.fixture(scope='session')
def sora_cam_client():
    auth_key_id = os.environ.get(
        "SORACOM_AUTH_KEY_ID",
        "")
    auth_key = os.environ.get(
        "SORACOM_AUTH_KEY",
        "")
    client = sc(
        coverage_type='jp',
        auth_key_id=auth_key_id,
        auth_key=auth_key)
    logger.debug("client has been created")
    yield client


@pytest.fixture(scope="session", autouse=True)
def soracom_device(sora_cam_client):
    device_list = sora_cam_client.get_devices()
    device = None
    for dv in device_list:
        if dv.get('connected', True) and dv.get('deviceId', '') == _DEVICE_ID:
            device = dv
            break
    print(f'deviceId: {device} _DEVICE_ID: {_DEVICE_ID}')
    yield device.get('deviceId', '')


def download_file_and_check_mime_type(url, out_file):
    with tempfile.TemporaryDirectory() as dname:
        save_path = sc.download_file_from_url(url, dname)
        if save_path:
            if pathlib.Path(save_path).suffix == ".zip":
                logger.info("f_name: {save_path}")
                shutil.unpack_archive(save_path, dname)
                mime_type = 'video/mp4'
                files = glob.glob(dname+'/*.mp4')
                shutil.move(files[-1], out_file)
            else:
                shutil.move(save_path, out_file)
                mime_type = 'image/jpeg'
            if filetype.guess(out_file).mime != mime_type:
                logger.error(f"mime type {0} is not expected type {1}".
                             format(filetype.guess(out_file).mime, mime_type))
                return False
            else:
                return True
