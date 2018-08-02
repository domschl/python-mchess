import logging

try:
    from bluepy.btle import Scanner, DefaultDelegate, Peripheral
    bluepy_ble_support = True
except:
    bluepy_ble_support = False


class Transport():
    def __init__(self, que):
        if bluepy_ble_support == False:
            self.init = False
            return
        self.que = que  # asyncio.Queue()
        self.init = True
        logging.debug("bluepy_ble init ok")

    def search_board(self):
        logging.debug("bluepy_ble: searching for boards")

        class ScanDelegate(DefaultDelegate):
            def __init__(self):
                DefaultDelegate.__init__(self)

            def handleDiscovery(self, dev, isNewDev, isNewData):
                if isNewDev:
                    logging.debug("Discovered device {}".format(dev.addr))
                elif isNewData:
                    logging.debug("Received new data from {}".format(dev.addr))

        scanner = Scanner().withDelegate(ScanDelegate())

        try:
            devices = scanner.scan(10.0)
        except Exception as e:
            logging.error(
                "BLE scanning failed. You might need to excecute the scan with root rights: {}".format(e))
            return None

        for bledev in devices:
            logging.debug("Device {} ({}), RSSI={} dB".format(
                bledev.addr, bledev.addrType, bledev.rssi))
            for (adtype, desc, value) in bledev.getScanData():
                logging.debug("  {} ({}) = {}".format(desc, adtype, value))
                if desc == "Complete Local Name":
                    if "MILLENNIUM CHESS" in value:
                        logging.info(
                            "Autodetected Millennium board at Bluetooth LE address: {}, signal strength (rssi): {}".format(
                                bledev.addr, bledev.rssi))
                        return bledev.addr
        return None

    class PeriDelegate(DefaultDelegate):
        def __init__(self, que):
            DefaultDelegate.__init__(self)
            self.que = que
            logging.debug("Init delegate for peri")
            # ... initialise here

        def handleNotification(self, cHandle, data):
            # print("Handle: {}, data: {}", cHandle, data)
            rcv = ""
            for b in data:
                rcv += chr(b & 127)
            logging.debug('BLE received [{}]'.format(rcv))
            self.que.put(rcv)
            # ... perhaps check cHandle
            # ... process 'data'

    def test_board(self, address):
        mil = Peripheral(address)
        mil.withDelegate(self.PeriDelegate(self.que))
        self.mil = mil
        services = mil.getServices()
        for ser in services:
            print(ser)
            chrs = ser.getCharacteristics()
            for chr in chrs:
                if chr.uuid == "49535343-1e4d-4bd9-ba61-23c647249616":  # TX char, rx for us
                    self.rx = chr
                    self.rxh = chr.getHandle()
                    # Enable notification magic:
                    mil.writeCharacteristic(
                        self.rxh+1, (1).to_bytes(2, byteorder='little'))
                if chr.uuid == "49535343-8841-43f4-a8d4-ecbe34729bb3":  # RX char, tx for us
                    self.tx = chr
                    self.txh = chr.getHandle()
                if chr.supportsRead():
                    logging.debug("  {} UUID={} {} -> {}".format(chr, chr.uuid,
                                                                 chr.propertiesToString(), chr.read()))
                else:
                    logging.debug("  {} UUID={}{}".format(
                        chr, chr.uuid, chr.propertiesToString()))
            cc = ser.getCharacteristics(
                forUUID='00002902-0000-1000-8000-00805f9b34fb')
            if len(cc) > 0:
                print("found the ccc")
                self.ccc = cc[0]
            else:
                print("no ccc")
        return True

    def get_name(self):
        return "millcon_bluepy_ble"

    def is_init(self):
        return self.init
