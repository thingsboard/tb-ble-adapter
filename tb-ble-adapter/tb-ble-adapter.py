#!/usr/bin/env python

from btlewrap.bluepy import BluepyBackend
from tb_device_mqtt import TBDeviceMqttClient, TBPublishInfo
from bluepy.btle import DefaultDelegate, Peripheral, Scanner
from tb_gateway_mqtt import TBGatewayMqttClient
import time
import sys
import traceback
import json
import os
import importlib
import argparse


CURRENT_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser()

parser.add_argument("-s", "--server", default="localhost", help="server address, default \"localhost\"")
parser.add_argument("-p", "--port", type=int, default=1883, help="mqtt port, default 1883")
required = parser.add_argument_group("required arguments")
required.add_argument("-t", "--token", required=True, help="access token")

args = parser.parse_args()

#---------------------------------------------------------------------------------------------------

# Contains devices that we should connect to and extract data.
# Some aux data is written in runtime
known_devices = { }

#---------------------------------------------------------------------------------------------------

def ble_rescan(tb_gateway):
    # Scan for known devices

    class ScanDelegate(DefaultDelegate):
        def __init__(self):
            DefaultDelegate.__init__(self)

        def handleDiscovery(self, dev, isNewDev, isNewData):
            if isNewDev:
                print("Discovered BT device:", dev.addr)
            elif isNewData:
                print("Received new data from:", dev.addr)

    known_devices_found = False

    # Deactivate and clear existing devices before re-scanning
    for dev, dev_data in known_devices.items():
        for scanned, scanned_data in dev_data["scanned"].items():
            tb_name = scanned_data["tb_name"]

            tb_gateway.gw_connect_device(tb_name)

            tb_gateway.gw_send_attributes(tb_name, {"discovered": False})
            tb_gateway.gw_disconnect_device(tb_name)

        dev_data["scanned"].clear()

    while not known_devices_found:
        try:
            print("Scanning BLE devices...")
            scanner = Scanner().withDelegate(ScanDelegate())
            devices = scanner.scan(15.0)

            for dev in devices:
                print("Device {} ({}), RSSI={} dB".format(dev.addr, dev.addrType, dev.rssi))
                for (adtype, desc, value) in dev.getScanData():
                    print("  {} = {}".format(desc, value))
                    if desc == "Complete Local Name" and value in known_devices:
                        print("    [!] Known device found:", value)

                        tb_name = value + "_" + dev.addr.replace(':', '').upper()

                        known_devices[value]["scanned"][dev.addr] = {
                            "inst": known_devices[value]["extension"](),
                            "periph": Peripheral(),
                            "tb_name": tb_name
                        }

                        # Force TB to create a device
                        tb_gateway.gw_connect_device(tb_name)
                        tb_gateway.gw_send_attributes(tb_name, {"discovered": True,
                                                                "type": value,
                                                                "mac_addr": dev.addr,
                                                                "description": known_devices[value]["desription"]})
                        tb_gateway.gw_disconnect_device(tb_name)

                        known_devices_found = True
        except Exception as e:
            print("Exception caught:", e)

#---------------------------------------------------------------------------------------------------

def import_extension(name):
    return importlib.import_module("extensions." + name)

# Load extensions for interacting with devices

with open(CURRENT_SCRIPT_DIR + "/extensions/registered_extensions.json") as fl:  
    data = json.load(fl)
    for extension_name, extension_data in data.items():
        print("Loading", extension_name, "extension...")
        extension_module = import_extension(extension_name)
        extension_class = extension_module.Extension
        known_devices[extension_data["ble_name"]] = {
            "desription": extension_data["description"],
            "extension": extension_class,
            "scanned": {}
        }

rescan_required = True

def on_server_side_rpc_request(request_id, request_body):
    print("Received TB RPC call", request_body)
    if request_body["method"] == "doRescan":
        print("Scheduling rescan")
        global rescan_required
        rescan_required = True

gateway = TBGatewayMqttClient(args.server, args.token)
gateway.set_server_side_rpc_request_handler(on_server_side_rpc_request)
gateway.connect(port=args.port)

while True:
    if rescan_required:
        ble_rescan(gateway)
        rescan_required = False

    for type, type_data in known_devices.items():
        for dev_addr, dev_data in type_data["scanned"].items():
            try:
                instance = dev_data["inst"]
                ble_periph = dev_data["periph"]
                tb_dev_name = dev_data["tb_name"]

                telemetry = {}

                print("Connecting to device:", tb_dev_name)

                ble_periph.connect(dev_addr, "public")

                if instance.notify_supported():
                    if instance.notify_started() == False:
                        instance.start_notify(ble_periph)

                    class NotiDelegate(DefaultDelegate):
                        def __init__(self):
                            DefaultDelegate.__init__(self)
                            self.dev_instance = instance
                            self.telemetry = {}

                        def handleNotification(self, handle, data):
                            print("Received notifications for handle:", handle)
                            self.telemetry = self.dev_instance.handle_notify(handle, data)

                    print("Getting notification from:", tb_dev_name)

                    deleagate = NotiDelegate()
                    ble_periph.withDelegate(deleagate)
                    if ble_periph.waitForNotifications(1):
                        print("Data received:", deleagate.telemetry)

                    telemetry.update(deleagate.telemetry)

                print("Polling data from:", tb_dev_name)
                poll_telemetry = instance.poll(ble_periph)
                print("Data received:", poll_telemetry)

                telemetry.update(poll_telemetry)

                if not telemetry:
                    print("No data to send for current device")
                    continue

                gateway_pkt = { "ts": int(round(time.time() * 1000)), "values" : telemetry }

                print("Sending data to TB:", gateway_pkt)

                gateway.gw_connect_device(tb_dev_name)
                gateway.gw_send_telemetry(tb_dev_name, gateway_pkt)
                gateway.gw_disconnect_device(tb_dev_name)
            except KeyboardInterrupt:
                print("Exiting the application")
                sys.exit()
            except Exception as e:
                print("Exception caught:", e)
            finally:
                print("Disconnecting from device")
                ble_periph.disconnect()

    time.sleep(1)
