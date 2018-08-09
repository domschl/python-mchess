import bluetooth
try:
    from bluetooth.ble import DiscoveryService
    has_ble = True
except:
    has_ble = False
import logging


def bt_discover():
    nearby_devices = None
    try:
        nearby_devices = bluetooth.discover_devices(lookup_names=True)
    except Exception as e:
        logging.error("BT discovery failed: {}".format(e))
    return nearby_devices


def ble_discover():
    devices = None
    try:
        service = DiscoveryService()
        devices = service.discover(2)
    except Exception as e:
        logging.error("BLE discovery failed: {}".format(e))
    return devices


if __name__ == "__main__":
    logging.info("Bluetooth")
    nearby_devices = bt_discover()

    if nearby_devices is not None:
        print("found %d devices" % len(nearby_devices))

        for addr, name in nearby_devices:
            print("  %s - %s" % (addr, name))

    if has_ble is True:
        logging.info("Bluetooth LE")
        devices = ble_discover()
        if devices is not None:
            for address, name in devices.items():
                print("name: {}, address: {}".format(name, address))
    else:
        logging.info("BLE not available.")
