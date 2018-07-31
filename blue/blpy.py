from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import time
import struct


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
                    return dev
    return None


class PeriDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
        print("Init delegate for peri")
        # ... initialise here

    def handleNotification(self, cHandle, data):
        print("Handle: {}, data: {}", cHandle, data)
        # ... perhaps check cHandle
        # ... process 'data'


class BLE:

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.tx = None
        self.rx = None
        self.init = False
        mildev = find_millennium()
        if mildev != None:
            print("Millennium chess board at {}, rssi={}".format(
                mildev.addr, mildev.rssi))

            mil = Peripheral(mildev.addr)
            mil.withDelegate(PeriDelegate())
            self.mil = mil
            services = mil.getServices()
            for ser in services:
                print(ser)
                chrs = ser.getCharacteristics()
                for chr in chrs:
                    if chr.uuid == "49535343-1e4d-4bd9-ba61-23c647249616":  # TX char, rx for us
                        self.rx = chr
                        self.rxh = chr.getHandle()
                        mil.writeCharacteristic(
                            self.rxh+1, (1).to_bytes(2, byteorder='little'))
                    if chr.uuid == "49535343-8841-43f4-a8d4-ecbe34729bb3":  # RX char, tx for us
                        self.tx = chr
                        self.txh = chr.getHandle()
                    if chr.supportsRead():
                        print("  {} UUID={} {} -> {}".format(chr, chr.uuid,
                                                             chr.propertiesToString(), chr.read()))
                    else:
                        print("  {} UUID={}{}".format(
                            chr, chr.uuid, chr.propertiesToString()))
                cc = ser.getCharacteristics(
                    forUUID='00002902-0000-1000-8000-00805f9b34fb')
                if len(cc) > 0:
                    print("found the ccc")
                    self.ccc = cc[0]
                else:
                    print("no ccc")
            self.init = True

    def add_odd_par(self, b):
        byte = ord(b) & 127
        par = 1
        for _ in range(7):
            bit = byte & 1
            byte = byte >> 1
            par = par ^ bit
        if par == 1:
            # byte = ord(b) & 127
            byte = ord(b) | 128
        else:
            byte = ord(b) & 127
        return byte

    def hexd(self, digit):
        if digit < 10:
            return chr(ord('0')+digit)
        else:
            return chr(ord('A')-10+digit)

    def hex(self, num):
        d1 = num//16
        d2 = num % 16
        s = self.hexd(d1)+self.hexd(d2)
        return s

    def write(self, msg):
        if self.init:
            gpar = 0
            for b in msg:
                gpar = gpar ^ ord(b)
            msg = msg+self.hex(gpar)
            print("Msg: <{}>".format(msg))
            bts = ""
            for c in msg:
                bo = chr(self.add_odd_par(c))
                bts += bo
            try:
                btsx = bts.encode('latin1')
                print("Sent: <{}>".format(btsx))
                # enable notifications magic
                # self.tx.write(struct.pack('<bb', 0x01, 0x00))
                # self.mil.writeCharacteristic(self.ccc, struct.pack(
                #     '<bb', 0x01, 0x00), withResponse=True)
                self.tx.write(btsx, withResponse=True)
            except (Exception) as e:
                if self.verbose:
                    print("Failed to write {}: {}", msg, e)
        else:
            if self.verbose:
                print("No open port for write")

    def read(self, cmd, num):
        rep = []
        if self.init:
            rep = self.rx.read()
            print("Got: <{}> len={}".format(rep, len(rep)))
            ans = ""
            for i in range(len(rep)):
                ans += chr(rep[i] & 127)
            print("Dec: {}".format(ans))
        else:
            if self.verbose:
                print("No open port for read")
        if len(ans) > 2:
            gpar = 0
            for b in ans[:-2]:
                gpar = gpar ^ ord(b)
            if ans[-2]+ans[-1] != self.hex(gpar):
                if self.verbose:
                    print("CRC error rep={} CRCs: {}!={}".format(ans,
                                                                 ord(ans[-2]), self.hex(gpar)))
                return []
        return rep

    def get_version(self):
        # evmutex.acquire()
        version = ""
        self.write("V")
        return
        time.sleep(0.2)
        version = self.read('v', 7)
        if len(version) != 7:
            # evmutex.release()
            return ""
        if version[0] != 'v':
            # evmutex.release()
            return ""
        version = '{}.{}'.format(version[1]+version[2], version[3]+version[4])
        # evmutex.release()
        return version

    def get_position_raw_once(self):
        # evmutex.acquire()
        cmd = "S"
        self.write(cmd)
        return
        rph = self.read('s', 67)
        if len(rph) != 67:
            # evmutex.release()
            return ""
        if rph[0] != 's':
            # evmutex.release()
            return ""
        # evmutex.release()
        return rph[1:65]


ble = BLE()
ble.get_version()
ble.get_position_raw_once()
while True:
    if ble.mil.waitForNotifications(1.0):
        # handleNotification() was called
        continue

    print("Waiting...")
    # Perhaps do something else here
