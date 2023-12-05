#!/usr/bin/env python3

import os
import time
import unittest.mock as mock
from unittest.mock import patch
import pytest
import soracam as sc
from concurrent.futures import ThreadPoolExecutor, as_completed

from .conftest import (
    _VIDEO_DURATION,
    _VIDEO_OFFSET,
    _BEFOR_ONE_WEEK_FROM_T,
    logger,
    download_file_and_check_mime_type,
)


# Mocking requests for testing
@patch("requests.post")
def test_soracam_headers(mock_post):
    mock_post.return_value.json.return_value = {
        "apiKey": "test_key",
        "token": "test_token",
    }
    client = sc.SoraCamClient("jp", "auth_key_id", "auth_key")
    headers = next(client._soracom_headers())
    assert headers["X-Soracom-API-Key"] == "test_key"
    assert headers["X-Soracom-Token"] == "test_token"


def test_soracam_get_devices(sora_cam_client):
    device_list = sora_cam_client.get_devices()
    assert len(device_list)


def test_soracam_get_device(sora_cam_client, soracom_device):
    device_info = sora_cam_client.get_device(soracom_device)
    assert device_info.get("deviceId") == soracom_device


def test_get_offline_devices(sora_cam_client):
    device_list = sora_cam_client.get_devices()
    off_device_list = sora_cam_client.get_offline_devices()
    off_line = False
    for dv in device_list:
        if not dv.get("connected", True):
            off_line = True
            break
    if off_line:
        assert len(off_device_list), "there should be no offline device"
    else:
        assert not len(
            off_device_list
        ), "there should be more than one offline device"


def test_get_devices_events(sora_cam_client, soracom_device):
    # assume there are several device events,
    # otherwise the tests fails
    device_event = sora_cam_client.get_devices_events(
        soracom_device, limit=100
    )
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), "there should be device_event"


def test_get_devices_events_with_label(sora_cam_client, soracom_device):
    # assume there are events with person label,
    # otherwise the tests fails
    device_event = sora_cam_client.get_devices_events(
        soracom_device, limit=100, label="person"
    )
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), "there should be device_event with person"


def test_get_devices_events_with_from_to(sora_cam_client, soracom_device):
    # assume there are several device events,
    # otherwise the tests fails
    from_t = _BEFOR_ONE_WEEK_FROM_T
    to_t = int(time.time()) * 1000
    device_event = sora_cam_client.get_devices_events(
        soracom_device,
        from_t=from_t,
        to_t=to_t,
        limit=100,
        sort="desc",
        label="motion",
    )
    logger.debug(f"devices events: {device_event}")
    assert len(device_event), "there should be device_event"


def test_post_and_get_images_export_requests(sora_cam_client, soracom_device):
    res = sora_cam_client.post_images_export_requests(soracom_device, True)
    logger.debug(f"response: {res}")
    export_id = res.get("exportId", "")
    assert export_id, "exportId must be included"
    res = sora_cam_client.get_images_exports(soracom_device, export_id)
    assert len(res), "result must be included"
    url = res.get("url", "")
    assert download_file_and_check_mime_type(
        url, "out.jpg"
    ), f"failed to download from {url}"


def test_post_and_get_videos_export_requests(sora_cam_client, soracom_device):
    from_t = int((time.time() - _VIDEO_DURATION - _VIDEO_OFFSET) * 1000)
    to_t = from_t + _VIDEO_DURATION

    res = sora_cam_client.post_videos_export_requests(
        soracom_device, from_t, to_t
    )
    logger.debug(f"response: {res}")
    export_id = res.get("exportId", "")
    assert export_id, "exportId must be included"
    res = sora_cam_client.get_videos_exports(soracom_device, export_id)
    assert len(res), "result must be included"
    url = res.get("url", "")
    assert (
        download_file_and_check_mime_type(url, "out.zip") is True
    ), f"failed to download from {url}"


def test_check_export_status_timeout(soracom_device):
    mock_get = mock.Mock(return_value={"status": "not completed"})
    # Use the patch method to replace _get with your mock
    with mock.patch.object(sc.SoraCamClient, "_get", new=mock_get):
        instance = sc.SoraCamClient("jp", "auth_key_id", "auth_key")
        sc.WAITE_TIMEOUT = 1
        sc.LOOP_WAITE_TIME = 0.5
        with pytest.raises(sc.ExportTimeoutError):
            instance._check_export_status(
                device_id=soracom_device,
                export_id="export",
                media="media",
                expected="completed",
            )


def test_negative_check_export_status_failed(sora_cam_client, soracom_device):
    mock_get = mock.Mock(return_value={"status": "failed"})
    with mock.patch.object(sc.SoraCamClient, "_get", new=mock_get):
        instance = sc.SoraCamClient("jp", "auth_key_id", "auth_key")
        with pytest.raises(sc.ExportFailedError):
            instance._check_export_status(
                device_id=soracom_device,
                export_id="export",
                media="media",
                expected="completed",
            )


@pytest.mark.skipif(
    "NEGATIVE_TEST" not in os.environ,
    reason="NEGATIVE_TEST \
    environment variable is not set",
)
def test_negative_post_videos_export_requests_parallel(
    sora_cam_client, soracom_device
):
    from_t = int((time.time() - _VIDEO_DURATION - _VIDEO_OFFSET) * 1000)
    to_t = from_t + _VIDEO_DURATION
    export_request = (soracom_device, from_t, to_t)
    tasks = []
    for _ in range(10):
        tasks.append(export_request)
    with ThreadPoolExecutor() as executor:
        results = [
            executor.submit(sora_cam_client.post_videos_export_requests, *task)
            for task in tasks
        ]
        for res in as_completed(results):
            try:
                export_id = res.get("exportId", "")
                print("task returned: ", export_id)
            except Exception as error:
                print(f"task generated an exception: {error}")


def test_get_device_recordings_and_events(sora_cam_client, soracom_device):
    res = sora_cam_client.get_device_recordings_and_events(soracom_device)
    logger.debug(f"device recordings and events: {res}")
    assert len(res), "failed receive recordings and events"


def test_get_device_recordings_and_events_with_from_t(
    sora_cam_client, soracom_device
):
    from_t = _BEFOR_ONE_WEEK_FROM_T
    to_t = int(time.time()) * 1000
    res = sora_cam_client.get_device_recordings_and_events(
        soracom_device, from_t=from_t, to_t=to_t, sort="desc"
    )
    logger.debug(f"device recordings and events: {res}")
    assert len(res), "failed receive recordings and events"


settings_test_cases = [
    ("logo", {"state": "off"}, {"state": "off"}),
    ("motion_tagging", {"state": "off"}, {"state": "off"}),
    ("night_vision", {"state": "auto"}, {"state": "auto"}),
    ("quality", {"state": "high"}, {"state": "high"}),
    ("rotation", {"state": 0}, {"state": 0}),
    ("status_light", {"state": "on"}, {"state": "on"}),
    ("timestamp", {"state": "on"}, {"state": "on"}),
]


@pytest.mark.parametrize(
    "setting, payload, expected_get_response", settings_test_cases
)
def test_post_and_get_settings(
    sora_cam_client, soracom_device, setting, payload, expected_get_response
):
    res = sora_cam_client.post_settings(soracom_device, setting, payload)
    assert res == {}, f"Expected an empty dict, but got: {res}"
    res = sora_cam_client.get_settings(soracom_device, setting)
    assert (
        res == expected_get_response
    ), f"Expected state {expected_get_response}, but got: {res}"


def test_get_settings_contains_keys(sora_cam_client, soracom_device):
    res = sora_cam_client.get_settings(device_id=soracom_device)
    logger.debug(f"device settings: {res}")
    keys_to_check = [
        "logo",
        "motionTagging",
        "nightVision",
        "rotation",
        "statusLight",
        "timestamp",
    ]
    assert all(
        key in res for key in keys_to_check
    ), f"Not all expected keys are present in the res: {res}"
