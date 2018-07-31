from bluepy.btle import Scanner, DefaultDelegate


def find_millennium(verbose=False):
    class ScanDelegate(DefaultDelegate):
        def __init__(self):
            DefaultDelegate.__init__(self)

        def handleDiscovery(self, dev, isNewDev, isNewData):
            if isNewDev:
                if verbose is True:
                    print("Discovered device {}".format(dev.addr))
            elif isNewData:
                if verbose is True:
                    print("Received new data from {}".format(dev.addr))

    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)

    for dev in devices:
        if verbose is True:
            print("Device {} ({}), RSSI={} dB".format(
                dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            if verbose is True:
                print("  {} = {}".format(desc, value))
            if desc == "Complete Local Name":
                if "MILLENNIUM CHESS" in value:
                    return dev.addr, dev.rssi
    return None, None


addr, rssi = find_millennium()
if addr != None:
    print("Millennium chess board at {}, rssi={}".format(addr, rssi))
