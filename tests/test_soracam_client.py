#!/usr/bin/env python3

import time
from unittest.mock import patch

import soracam as sc

from .conftest import (
    _VIDEO_DURATION, _VIDEO_OFFSET, logger, download_file_and_check_mime_type)


# Mocking requests for testing
@patch('requests.post')
def test_soracam_headers(mock_post):
    mock_post.return_value.json.return_value = {
        'apiKey': 'test_key',
        'token': 'test_token'
    }
    client = sc('jp', 'auth_key_id', 'auth_key')
    headers = next(client._soracom_headers())
    assert headers['X-Soracom-API-Key'] == 'test_key'
    assert headers['X-Soracom-Token'] == 'test_token'


def test_soracam_get_devices(sora_cam_client):
    device_list = sora_cam_client.get_devices()
    assert len(device_list)


def test_soracam_get_device(sora_cam_client, soracom_device):
    device_info = sora_cam_client.get_device(soracom_device)
    assert device_info.get('deviceId') == soracom_device


def test_get_offline_devices(sora_cam_client):
    device_list = sora_cam_client.get_devices()
    off_device_list = sora_cam_client.get_offline_devices()
    off_line = False
    for dv in device_list:
        if not dv.get('connected', True):
            off_line = True
            break
    if off_line:
        assert len(off_device_list), \
            "there should be no offline device"
    else:
        assert not len(off_device_list), \
            "there should be more than one offline device"


def test_get_devices_events(sora_cam_client, soracom_device):
    # assume there are several device events,
    # otherwise the tests fails
    device_event = sora_cam_client.get_devices_events(soracom_device)
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), \
        "there should be device_event"


def test_get_devices_events_with_label(sora_cam_client, soracom_device):
    # assume there are events with person label,
    # otherwise the tests fails
    device_event = \
        sora_cam_client.get_devices_events(
            soracom_device, limit=10, label='person')
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), \
        "there should be device_event with person"


def test_get_devices_events_with_from_to(sora_cam_client, soracom_device):
    # assume there are several device events,
    # otherwise the tests fails
    from_t = 1640962800 * 1000
    to_t = int(time.time()) * 1000
    device_event = sora_cam_client.get_devices_events(
        soracom_device, from_t=from_t, to_t=to_t, limit=3, sort='desc',
        label='motion')
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), \
        "there should be device_event"


def test_post_and_get_images_export_requests(
        sora_cam_client, soracom_device):
    res = sora_cam_client.post_images_export_requests(
        soracom_device, True)
    logger.debug(f"response: {res}")
    export_id = res.get('exportId', '')
    assert export_id, \
        "exportId must be included"
    res = sora_cam_client.get_images_exports(soracom_device, export_id)
    assert len(res), \
        "result must be included"
    url = res.get('url', '')
    assert download_file_and_check_mime_type(url, 'out.jpg'), \
        f"failed to download from {url}"


def test_post_and_get_videos_export_requests(
        sora_cam_client, soracom_device):
    from_t = int((time.time() - _VIDEO_DURATION - _VIDEO_OFFSET)*1000)
    to_t = from_t + _VIDEO_DURATION

    res = sora_cam_client.post_videos_export_requests(
        soracom_device, from_t, to_t)
    logger.debug(f"response: {res}")
    export_id = res.get('exportId', '')
    assert export_id, \
        "exportId must be included"
    res = sora_cam_client.get_videos_exports(soracom_device, export_id)
    assert len(res), \
        "result must be included"
    url = res.get('url', '')
    assert download_file_and_check_mime_type(url, 'out.zip') is True, \
        f"failed to download from {url}"
