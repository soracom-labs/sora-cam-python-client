# SoraCam Python Client

This python library provides a client to interact with [SoraCam API](https://users.soracom.io/ja-jp/tools/api/reference/#/SoraCam). It allows to make authenticated requests to the API and handle the response.

## Features

- `get_devices`: Gets the list of devices information.
- `get_device`: Gets the device information.
- `get_offline_devices`: GGets the list of offline devices.
- `get_devices_events`: Gets the events of a device.
- `get_stream`: Sends a get stream request from recorded video.
- `post_videos_export_requests`: Sends an exporting video request from recorded video.
- `get_videos_exports`: Return the result of the video exports request.
- `post_images_export_requests`: Exports a image from a recorded video
- `get_images_exports`: Return the result of the images exports request.
- `download_file_from_url`: Downloads a file from the specified URL and saves it to the specified
        path.
- `get_device_recordings_and_events`: Gets the device recordings duration and events.
- `get_settings`: Gets the settings of sora_cam.
- `post_settings`: Sends a request to change settings of sora_cam.


## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install SoraCam Python Client.

```bash
pip install git+https://github.com/soracom-labs/sora-cam-python-client
```

## Usage

```python
import soracam as sc

# create soracam client
clinet = sc.SoraCamClient(
        coverage_type='jp',
        auth_key_id=auth_key_id,
        auth_key=auth_key)

# get device list
device_list = client.get_devices()

```
For more information, please see docstring in [soracam_api.py](https://github.com/soracom-labs/sora-cam-python-client/soracam/soracom_api.py)

## Configuration

The following environment variables can be used to configure the client:

- `SORACOM_ENDPOINT`: Endpoint to connect to the SORACOM API server (default: https://%s.api.soracom.io/).
- `MAX_RETRIES`: API retries if HTTPError is returned (default: 3).
- `REQUESTS_TIMEOUT`: Timeout for API requests (default: 60).

## License
This project is open source and available under the MIT License.
