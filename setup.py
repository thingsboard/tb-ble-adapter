from setuptools import setup, find_packages

setup(
  name = 'tb-ble-adapter',
  packages = [ 'tb-ble-adapter', 'tb-ble-adapter/extensions' ],
  version = '1.6.0',
  license='Apache',
  description = 'BLE adapter demo, that connects to available devices and sends data from them to ThingsBoard server',
  author = 'ThingsBoard',
  author_email = 'support@thingsboard.io',
  url = 'https://github.com/thingsboard/tb-ble-adapter',
  download_url = 'https://github.com/thingsboard/tb-ble-adapter',
  keywords = ['tb-ble-adapter', 'demo', 'bluetooth low energy', 'thingsboard'],
  install_requires=[
          'btlewrap',
          'bluepy',
          'bt-mqtt-client',
      ],
  classifiers=[
    'Intended Audience :: Developers',
    'Programming Language :: Python :: 3.4',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
  ],
)
