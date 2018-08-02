import logging

import mill_prot
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
        self.is_open = False
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
            self.chunks = ""
            # ... initialise here

        def handleNotification(self, cHandle, data):
            logging.debug("BLE: Handle: {}, data: {}".format(cHandle, data))
            rcv = ""
            for b in data:
                rcv += chr(b & 127)
            logging.debug('BLE received [{}]'.format(rcv))
            self.chunks += rcv
            if self.chunks[0] not in mill_prot.millennium_protocol_replies:
                logging.warning(
                    "Illegal reply start '{}' received, discarding".format(self.chunks[0]))
                while len(self.chunks) > 0 and self.chunks[0] not in mill_prot.millennium_protocol_replies:
                    self.chunks = self.chunks[1:]
            if len(self.chunks) > 0:
                mlen = mill_prot.millennium_protocol_replies[self.chunks[0]]
                if len(self.chunks) >= mlen:
                    valmsg = self.chunks[:mlen]
                    logging.debug(
                        'bluepy_ble received complete msg: {}'.format(valmsg))
                    if mill_prot.check_block_crc(valmsg):
                        self.que.put(valmsg)
                    self.chunks = self.chunks[mlen:]

    def test_board(self, address):
        logging.debug("Testing ble at {}".format(address))
        if self.open_mt(address) is True:
            self.is_open = True
            return "1.0"
        else:
            return None

    def open_mt(self, address):
        if self.is_open is False:
            try:
                self.mil = Peripheral(address)
            except Exception as e:
                logging.warning(
                    'Failed to create ble peripheral at {}'.format(address))
                self.mil = None
                return False
        try:
            self.mil.withDelegate(self.PeriDelegate(self.que))
        except Exception as e:
            logging.error(
                'Failed to install peripheral delegate! {}'.format(e))
            self.mil = None
            return False
        try:
            services = self.mil.getServices()
        except:
            logging.error(
                'Failed to enumerate services for {}, {}'.format(address, e))
            return False
        for ser in services:
            logging.debug('Service: {}'.format(ser))
            chrs = ser.getCharacteristics()
            for chr in chrs:
                if chr.uuid == "49535343-1e4d-4bd9-ba61-23c647249616":  # TX char, rx for us
                    self.rx = chr
                    self.rxh = chr.getHandle()
                    # Enable notification magic:
                    logging.debug('Enabling notifications')
                    self.mil.writeCharacteristic(
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
            # cc = ser.getCharacteristics(
            #     forUUID='00002902-0000-1000-8000-00805f9b34fb')
            # if len(cc) > 0:
            #     logging.debug("Found characteric.")
            #     self.ccc = cc[0]
            # else:
            #     logging.debug("no ccc characteric")
        return True

    def write_mt(self, msg):
        if self.mil is not None:
            gpar = 0
            for b in msg:
                gpar = gpar ^ ord(b)
            msg = msg+mill_prot.hex2(gpar)
            logging.debug("blue_ble write: <{}>".format(msg))
            bts = ""
            for c in msg:
                bo = chr(mill_prot.add_odd_par(c))
                bts += bo
            try:
                btsx = bts.encode('latin1')
                logging.debug("Sending: <{}>".format(btsx))
                self.tx.write(btsx, withResponse=True)
            except Exception as e:
                logging.error(
                    "bluepy_ble: failed to write {}: {}".format(msg, e))
        else:
            logging.error("No open pheripheral for write")

    def get_name(self):
        return "millcon_bluepy_ble"

    def is_init(self):
        return self.init
