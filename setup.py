from setuptools import setup, find_packages

setup(
    name='soracam-python-client',
    version='0.0.1',
    url='https://github.com/soracom-labs/sora-cam-python-client',
    author='Ken Igarashi',
    author_email='sccs@soracom.jp',
    description='python soracam client library',
    packages=find_packages(),
    install_requires=['requests'],
    python_requires='>=3.9',
)
