from distutils.core import setup
setup(
  name = 'tb-ble-adapter',
  version = '0.1',
  license='Apache',
  description = 'ble adapter demo, that connects to available devices and sends data from them to thingsboard server',
  author = '',
  author_email = '',
  url = '',
  download_url = '',
  keywords = ['tb-ble-adapter', 'demo', 'bluetooth low energy'],
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
