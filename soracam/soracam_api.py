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
import soracam

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

        self.request_headers = {'Content-type': 'application/json'}
        self.api_endpoint = "https://%s.api.soracom.io/" % coverage_type
        self.auth_key_id = auth_key_id
        self.auth_key = auth_key

    def _soracom_headers(self):
        url = urljoin(self.api_endpoint, 'v1/auth')
        payload = {
            "authKeyId": self.auth_key_id,
            "authKey": self.auth_key
        }
        try:
            response = requests.post(
                url=url, json=payload,
                timeout=soracam.REQUESTS_TIMEOUT)
        except Exception as error:
            logger.error(f"failed to authenticate: {error}")
            raise error
        param = response.json()
        headers = {
            'X-Soracom-API-Key': param.get('apiKey'),
            'X-Soracom-Token': param.get('token'),
            'accept': "application/json",
            'Content-Type': "application/json"
        }
        yield headers

    def _get(self, url: str, params: dict = {}) -> dict:
        """
        Sends a GET request to a URL.

        Parameters:
            url (str): The URL to send the request to.
            params (dict): The path parameters
        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the GET request.
        """
        try:
            response = requests.get(
                url=url, headers=next(self._soracom_headers()),
                timeout=soracam.REQUESTS_TIMEOUT, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            logger.error(f"get request for {url} failed: {err}")
            logger.error(f"response: {response.text}")
            raise

    def _post(self, url: str, payload: str) -> dict:
        """
        Sends a POST request to a URL.

        Parameters:
            url (str): The URL to send the request to.
            payload (dict): The payload to include in the request.

        Returns:
            dict: The response from the API returned by JSON.

        Raises:
            Exception: If an error occurs while sending the POST request.
        """
        logger.debug(f"payload: {payload}")
        try:
            response = requests.post(
                url=url, headers=next(self._soracom_headers()),
                json=payload, timeout=soracam.REQUESTS_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            logger.error(f"post request for {url} failed: {err}")
            logger.error(f"response: {response.text}")
            raise

    def _check_export_status(self, device_id: str, export_id: str,
                             media: str, expected: str = "completed") -> bool:
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
            soracam.ExportFailedError: If the export process fails.
            soracam.ExportTimeoutError: If checking the export status
            timeout.
        """

        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, media, "exports", export_id)
        url = urljoin(self.api_endpoint, path)
        start_time = time.time()
        while (time.time() - start_time < soracam.WAITE_TIMEOUT):
            response = self._get(url)
            logger.debug("export status: {}".format(response))
            status = response.get('status', '')
            if status == expected:
                return True
            elif status == "failed":
                raise soracam.ExportFailedError(
                    f"Export failed for device {device_id}, \
                    export {export_id}")
            time.sleep(soracam.LOOP_WAITE_TIME)
        raise soracam.ExportTimeoutError(
            f"Checking export status timed out \
            for device {device_id}, export {export_id}")

    @staticmethod
    def download_file_from_url(target_url: str, target_directory: str) -> str:
        """
        Downloads a file from the specified URL and saves it to the specified
        path.

        This function downloads a file in chunks, which can be more efficient
        than downloading the entire file in one go, especially for large files.

        Parameters:
        target_url (str): The URL of the file to download.
        target_directory (str): The directory where the downloaded file should
        be saved.

        Returns:
        str: Filepath if the file was downloaded and saved successfully.

        Raises:
        requests.exceptions.HTTPError: If an HTTP error occurs while trying to
        download the file.
        """

        try:
            response = requests.get(target_url, stream=True)
        except requests.exceptions.HTTPError as err:
            logger.error("download file from {0} failed: {1}"
                         .format(target_url, err))
            raise
        path = urlparse(target_url).path
        filename = unquote(path.split("/")[-1])
        save_path = os.path.join(target_directory, filename)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
            return save_path

    def post_images_export_requests(
            self, device_id: str, wide_angle_correction: bool = True,
            export_time: int = 0) -> dict:
        """
        Start the process of exporting still images from recorded video
        saved by cloud continuous recording.

        Parameters:
        device_id (str): The unique identifier for the camera device.
        wide_angle_correction (bool): Enable wide_angle_correction.
        export_time (int): The target export time

        Returns:
        dict: The response from the API including containing the result
        of export request.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """

        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, 'images/exports')
        url = urljoin(self.api_endpoint, path)
        if not export_time:
            export_time = int(time.time()) * 1000
        payload = {}
        payload['time'] = export_time
        if wide_angle_correction:
            payload['imageFilters'] = ["wide_angle_correction"]
        return self._post(url, payload)

    def get_images_exports(
            self, device_id: str, export_id: str) -> dict:
        """
        Return the result of the get images exports request and error
        is returned if the process status doesn't change for a while.

        Parameters:
        device_id (str): The unique identifier for the camera device.
        export_id (str): The unique identifier for the export process.

        Returns:
        dict: The response from the API, containing the exported image's
        data or status information. If the export process is not complete,
        returns None.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """

        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, 'images/exports', export_id)
        url = urljoin(self.api_endpoint, path)
        if self._check_export_status(device_id, export_id,
                                     soracam.MEDIA_IMAGE):
            return self._get(url)

    def get_stream(
            self, device_id: str, from_t: int, to_t: int) -> dict:
        """
        Retrieves a stream from a specific device for a given time range.

        Parameters:
            device_id (str): The unique identifier for the device.
            from_t (int): The start timestamp of the stream.
            to_t (int): The end timestamp of the stream.

        Returns:
            dict: The response from the API, containing the stream data.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """
        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, 'stream')
        url = urljoin(self.api_endpoint, path)

        payload = {
            "from": from_t,
            "to": to_t
        }
        return self._post(url, payload)

    def post_videos_export_requests(
            self, device_id: str, from_t: int, to_t: int) -> dict:
        """
        Start the process of exporting video from recorded video
        saved by cloud continuous recording.

        Parameters:
        device_id (str): The unique identifier for the camera device.
        from_t (int): The start timestamp of the stream.
        to_t (int): The end timestamp of the stream.

        Returns:
        dict: The response from the API including containing the result
        of export request.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """

        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, 'videos/exports')
        url = urljoin(self.api_endpoint, path)

        payload = {
            "from": from_t,
            "to": to_t
        }
        return self._post(url, payload)

    def get_videos_exports(
            self, device_id: str, export_id: str) -> dict:
        """
        Return the result of the get videos exports request and error
        is returned if the process status doesn't change for a while.

        Parameters:
        device_id (str): The unique identifier for the camera device.
        export_id (str): The unique identifier for the export process.

        Returns:
        dict: The response from the API, containing the exported image's
        data or status information. If the export process is not complete,
        returns None.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """

        path = os.path.join(soracam.SORA_CAM_BASE_URL,
                            device_id, 'videos/exports', export_id)
        url = urljoin(self.api_endpoint, path)
        if self._check_export_status(device_id, export_id,
                                     soracam.MEDIA_VIDEO):
            return self._get(url)

    def get_devices(self) -> dict:
        """
        Gets the list of devices.

        Returns:
            dict: Dictionary contains the list of devices.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """
        url = urljoin(self.api_endpoint, soracam.SORA_CAM_BASE_URL)
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
            if not dv.get('connected', True):
                device_status = {}
                device_status['device_name'] = dv.get('name', None)
                device_status['device_id'] = dv.get('deviceId', None)
                device_status['last_connection'] = dv.get(
                    'lastConnectedTime', None)
                off_line_devices.append(device_status)
        return off_line_devices

    def get_devices_events(self, device_id: str = None, limit: int = 10,
                           sort: str = 'desc', label: str = None,
                           from_t: int = None, to_t: int = None) -> dict:
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
            dict: Dictionary contains the list of events of the device.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """
        path = os.path.join(soracam.SORA_CAM_BASE_URL, 'events') \
            if not device_id else os.path.join(
            soracam.SORA_CAM_BASE_URL, device_id, 'events')
        url = urljoin(self.api_endpoint, path)
        # create path parameters
        params = {'limit': limit}
        params['sort'] = sort
        if from_t:
            params['from'] = from_t
        if to_t:
            params['to'] = to_t
        params['search_type'] = 'or'
        events = self._get(url, params)
        if label:
            return [ev for ev in events if label in ev.get(
                'eventInfo', {}).get('atomEventV1', {}).get('labels', [])]
        return events

    def get_device(self, device_id=None) -> dict:
        """
        Gets the device information.

        Returns:
            dict: Dictionary contains the device information.

        Raises:
            Exception: If an error occurs while sending the POST request or
            processing the response.
        """
        # Join base_url and endpoint
        device_path = os.path.join(soracam.SORA_CAM_BASE_URL, device_id)
        url = urljoin(self.api_endpoint, device_path)
        return self._get(url)
