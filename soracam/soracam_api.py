#!/usr/bin/env python3

"""
This module provides a client to interact with SoraCam API. It allows
to make authenticated requests to the API and handle the response.
"""

import os
import logging
import time
from urllib.parse import urljoin
import requests
from urllib.parse import unquote, urlparse
import soracam as sc


_DEBUG = os.environ.get("DEBUG", "True").lower() in ["true", "1"]

# log settings
FORMAT = "%(levelname)s %(asctime)s \
          %(funcName)s %(filename)s %(lineno)d %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
if _DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

_REQUESTS_TIMEOUT = os.environ.get("REQUESTS_TIMEOUT", sc.REQUESTS_TIMEOUT)
_MAX_API_RETRIES = os.environ.get("MAX_API_RETRIES", sc.MAX_API_RETRIES)
_SORACOM_ENDPOINT = os.environ.get("SORACOM_ENDPOINT", sc.SORACOM_ENDPOINT)


class SoraCamClient(object):
    """
    A client to interact with the SoraCam API.

    Attributes:
        api_endpoint (str): The API endpoint to make requests.
        request_headers (dict): The headers to use for the requests.
    """

    def __init__(self, coverage_type: str, auth_key_id: str, auth_key: str):
        """
        Constructs all the necessary attributes for the SoraCamClient object.

        Parameters:
            coverage_type (str): The type of network coverage ('jp' or 'g').
            auth_key_id (str): The authentication key ID.
            auth_key (str): The authentication key.
        """

        self.request_headers = {"Content-type": "application/json"}
        self.api_endpoint = _SORACOM_ENDPOINT % coverage_type
        self.auth_key_id = auth_key_id
        self.auth_key = auth_key

    def _soracom_headers(self):
        """
        Generate the authentication headers required for API requests.

        Yields:
            dict: The headers to be used for authentication.
        """

        url = urljoin(self.api_endpoint, "v1/auth")
        payload = {"authKeyId": self.auth_key_id, "authKey": self.auth_key}
        try:
            response = requests.post(
                url=url, json=payload, timeout=_REQUESTS_TIMEOUT
            )
        except Exception as error:
            logger.error(f"failed to authenticate: {error}")
            raise error
        param = response.json()
        headers = {
            "X-Soracom-API-Key": param.get("apiKey"),
            "X-Soracom-Token": param.get("token"),
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        yield headers

    def _get(
        self, url: str, params: dict = {}, raw: bool = False
    ) -> dict | requests.Response:
        """
        Sends a GET request to URL.

        Parameters:
            url (str): The URL for the request send to.
            params (dict): The path parameters
            raw (bool): The flag to switch return types dict or Response.
        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        last_exception = None
        for _ in range(_MAX_API_RETRIES):
            try:
                response = requests.get(
                    url=url,
                    headers=next(self._soracom_headers()),
                    timeout=_REQUESTS_TIMEOUT,
                    params=params,
                )
                response.raise_for_status()
                return response if raw else response.json()
            except requests.exceptions.HTTPError as err:
                logger.error(f"get request for {url} failed: {err}")
                last_exception = err
                if response.status_code == 429:
                    time.sleep(sc.RETRY_INTERVAL)
                else:
                    raise
        raise last_exception

    def _post(self, url: str, payload: str) -> dict:
        """
        Sends a POST request to URL.

        Parameters:
            url (str): The URL to send the request to.
            payload (dict): The payload to include in the request.

        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the POST request.
        """

        last_exception = None
        for _ in range(_MAX_API_RETRIES):
            try:
                response = requests.post(
                    url=url,
                    headers=next(self._soracom_headers()),
                    json=payload,
                    timeout=_REQUESTS_TIMEOUT,
                )
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {}
            except requests.exceptions.HTTPError as err:
                logger.error(f"post request for {url} failed: {err}")
                last_exception = err
                if response.status_code == 429:
                    time.sleep(sc.RETRY_INTERVAL)
                else:
                    raise
        raise last_exception

    def _check_export_status(
        self,
        device_id: str,
        export_id: str,
        media: str,
        expected: str = "completed",
    ) -> bool:
        """
        Checks the export status of a device.

        Parameters:
            device_id (str): The unique identifier for the device.
            export_id (str): The unique identifier for the export process.
            media (str): The media type ('images' or 'videos').
            expected (str): The expected status of the export process.

        Returns:
            bool: True if the export process is complete, False otherwise.

        Raises:
            soracaom.SoraCamException.ExportFailedError: \
                If the export process fails.
            soracaom.SoraCamException.ExportTimeoutError: \
                If checking the export status times out.
        """

        path = os.path.join(
            sc.SORA_CAM_BASE_URL, device_id, media, "exports", export_id
        )
        url = urljoin(self.api_endpoint, path)
        start_time = time.time()
        wait_time = sc.LOOP_WAITE_SECOND
        while time.time() - start_time < sc.WAITE_TIMEOUT:
            response = self._get(url)
            logger.debug(f"export status: {response}")
            status = response.get("status", "")
            if status == expected:
                return True
            elif status == "failed":
                raise sc.ExportFailedError(
                    f"Export failed for device {device_id}, \
                    export {export_id}"
                )
            if wait_time <= sc.LOOP_WAITE_MAX_SECOND:
                wait_time += sc.LOOP_WAITE_SECOND
            time.sleep(wait_time)
        raise sc.ExportTimeoutError(
            f"Checking export status timed out \
            for device {device_id}, export {export_id}"
        )

    @staticmethod
    def download_file_from_url(target_url: str, target_directory: str) -> str:
        """
        Downloads a file from the specified URL and saves it to the specified
        path.

        Parameters:
            target_url (str): The URL of the file to download.
            target_directory (str): The directory where the downloaded file
            should be saved.

        Returns:
            str: Filepath if the file was downloaded and saved successfully.

        Raises:
            requests.exceptions.HTTPError: If an HTTP error occurs while
            trying to download the file.
        """

        path = urlparse(target_url).path
        filename = unquote(path.split("/")[-1])
        save_path = os.path.join(target_directory, filename)
        logger.debug(f"save file to: {save_path} from: {target_url}")
        try:
            with requests.get(
                target_url, stream=True, timeout=_REQUESTS_TIMEOUT
            ) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return save_path
        except requests.exceptions.HTTPError as err:
            logger.error(f"download file from {target_url} failed: {err}")
            raise

    def post_images_export_requests(
        self,
        device_id: str,
        wide_angle_correction: bool = True,
        export_time: int = 0,
    ) -> dict:
        """
        Sends an exporting image request from recorded video.

        Parameters:
            device_id (str): The unique identifier for the device.
            wide_angle_correction (bool): Enable wide_angle_correction.
            export_time (int): The target export time

        Returns:
            dict: The response from the API including containing the result
            of export request.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """

        path = os.path.join(sc.SORA_CAM_BASE_URL, device_id, "images/exports")
        url = urljoin(self.api_endpoint, path)
        if not export_time:
            export_time = int(time.time()) * 1000
        payload = {}
        payload["time"] = export_time
        if wide_angle_correction:
            payload["imageFilters"] = ["wide_angle_correction"]
        return self._post(url, payload)

    def get_images_exports(self, device_id: str, export_id: str) -> dict:
        """
        Return the result of the images exports request.

        Parameters:
            device_id (str): The unique identifier for the camera device.
            export_id (str): The unique identifier for the export process.

        Returns:
            dict: The response from the API, containing the exported image's
            status information. If there are no export processes,
            it returns None.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        path = os.path.join(
            sc.SORA_CAM_BASE_URL, device_id, "images/exports", export_id
        )
        url = urljoin(self.api_endpoint, path)
        if self._check_export_status(device_id, export_id, sc.MEDIA_IMAGE):
            return self._get(url)

    def get_stream(self, device_id: str, from_t: int, to_t: int) -> dict:
        """
        Sends a get stream request from recorded video.

        Parameters:
            device_id (str): The unique identifier for the device.
            from_t (int): The start timestamp of the stream.
            to_t (int): The end timestamp of the stream.

        Returns:
            dict: The response from the API, containing the stream data.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        path = os.path.join(sc.SORA_CAM_BASE_URL, device_id, "stream")
        url = urljoin(self.api_endpoint, path)

        payload = {"from": from_t, "to": to_t}
        return self._post(url, payload)

    def post_videos_export_requests(
        self, device_id: str, from_t: int, to_t: int
    ) -> dict:
        """
        Sends an exporting video request from recorded video.

        Parameters:
            device_id (str): The unique identifier for the camera device.
            from_t (int): The start timestamp of the stream.
            to_t (int): The end timestamp of the stream.

        Returns:
            dict: The response from the API including containing the result
            of export request.

        Raises:
            Exception: If an error occurs while sending the POST request.
        """

        path = os.path.join(sc.SORA_CAM_BASE_URL, device_id, "videos/exports")
        url = urljoin(self.api_endpoint, path)

        payload = {"from": from_t, "to": to_t}
        return self._post(url, payload)

    def get_videos_exports(self, device_id: str, export_id: str) -> dict:
        """
        Return the result of the video exports request.


        Parameters:
            device_id (str): The unique identifier for the device.
            export_id (str): The unique identifier for the export process.

        Returns:
            dict: The response from the API, containing the exported video's
            data or status information. If there are no export processes,
            it returns None.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        path = os.path.join(
            sc.SORA_CAM_BASE_URL, device_id, "videos/exports", export_id
        )
        url = urljoin(self.api_endpoint, path)
        if self._check_export_status(device_id, export_id, sc.MEDIA_VIDEO):
            return self._get(url)

    def get_devices(self) -> dict:
        """
        Gets the list of devices information.

        Returns:
            list: The list of devices.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        url = urljoin(self.api_endpoint, sc.SORA_CAM_BASE_URL)
        return self._get(url)

    def get_offline_devices(self) -> list:
        """
        Gets the list of offline devices.

        Returns:
            list: The list of offline devices.
        """

        off_line_devices = []
        device_list = self.get_devices()
        for dv in device_list:
            if not dv.get("connected", True):
                device_status = {}
                device_status["device_name"] = dv.get("name", None)
                device_status["device_id"] = dv.get("deviceId", None)
                device_status["last_connection"] = dv.get(
                    "lastConnectedTime", None
                )
                off_line_devices.append(device_status)
        return off_line_devices

    def fetch_paginated_data(self, url, init_params):
        params = init_params.copy()
        aggregated_data = []
        while True:
            response = self._get(url, params, True)
            if isinstance(response.json(), list):
                aggregated_data.extend(response.json())
            elif isinstance(response.json(), dict):
                aggregated_data.append(response.json())
            next_key = response.headers.get("x-soracom-next-key")
            if not next_key:
                break
            params["last_evaluated_key"] = next_key
        return aggregated_data

    def get_devices_events(
        self,
        device_id: str = None,
        limit: int = 10,
        sort: str = "desc",
        label: str = None,
        from_t: int = None,
        to_t: int = None,
    ) -> list:
        """
        Gets the events of a device.

        Parameters:
            device_id (str): The unique identifier for the device.
            limit (int): The number of events to return.
            sort (str): The sort order.
            label (str): The label for the event.
            from_t (int): The start timestamp for the events.
            to_t (int): The end timestamp for the the events.

        Returns:
            list: The list of event of the device.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        path = (
            os.path.join(sc.SORA_CAM_BASE_URL, "events")
            if not device_id
            else os.path.join(sc.SORA_CAM_BASE_URL, device_id, "events")
        )
        url = urljoin(self.api_endpoint, path)
        params = {"limit": limit, "sort": sort, "search_type": "or"}
        if from_t:
            params["from"] = from_t
        if to_t:
            params["to"] = to_t
        # repeat if the response header
        # contains the 'x-soracom-next-key' header.
        all_events = self.fetch_paginated_data(url, params)
        if label:
            return [
                ev
                for ev in all_events
                if label
                in ev.get("eventInfo", {})
                .get("atomEventV1", {})
                .get("type", [])
            ]
        else:
            return all_events

    def get_device(self, device_id=None) -> dict:
        """
        Gets the device information.

        Returns:
            dict: Th Dictionary contains the device information.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        device_path = os.path.join(sc.SORA_CAM_BASE_URL, device_id)
        url = urljoin(self.api_endpoint, device_path)
        return self._get(url)

    def get_device_recordings_and_events(
        self,
        device_id: str,
        from_t: int = None,
        to_t: int = None,
        sort: str = "desc",
    ) -> list:
        """
        Gets the device recordings duration and events.

        Parameters:
            device_id (str): The unique identifier for the device.
            from_t (int): The start timestamp for the recordings_and_events.
            to_t (int): The end timestamp for the recordings_and_events.
            sort (str): The sort order.

        Returns:
            list: The list of recordings duration and events of the device.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """
        path = os.path.join(
            sc.SORA_CAM_BASE_URL, device_id, "recordings_and_events"
        )
        url = urljoin(self.api_endpoint, path)
        params = {"sort": sort}
        if from_t:
            params["from"] = from_t
        if to_t:
            params["to"] = to_t

        # repeat if the response header
        # contains the 'x-soracom-next-key' header.
        all_recordings_and_events = self.fetch_paginated_data(url, params)
        return all_recordings_and_events

    def get_settings(self, device_id: str, setting: str = "") -> dict:
        """
        Gets the settings of sora_cam.

        Parameters:
            device_id (str): The unique identifier for the device.
            setting (str): Specify the kind of settings. ex: `timestamp`

        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """
        path_components = [
            sc.SORA_CAM_BASE_URL,
            device_id,
            "atomcam",
            "settings",
        ]
        if setting:
            path_components.append(setting)

        path = os.path.join(*path_components)
        url = urljoin(self.api_endpoint, path)
        return self._get(url)

    def post_settings(
        self, device_id: str, setting: str, payload: dict
    ) -> dict:
        """
        Sends a request to change settings of sora_cam.

        Parameters:
            device_id (str): The unique identifier for the device.
            setting (str): Specify the kind of settings. ex: `timestamp`

        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """

        path = os.path.join(
            sc.SORA_CAM_BASE_URL, device_id, "atomcam/settings/", setting
        )
        url = urljoin(self.api_endpoint, path)
        return self._post(url, payload)
