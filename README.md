# SoraCam Python Client

This python library provides a client to interact with the Soracom API. It allows to make authenticated requests to the API and handle the response.

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


## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install SoraCam Python Client.

```bash
pip install git+https://github.com/soracom-labs/sora-cam-python-client
