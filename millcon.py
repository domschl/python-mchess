import time
import os
import struct
import threading
import queue
import json

try:
    import chess
    import chess.uci
    chess_support = True
except:
    chess_support = False

try:
    import serial
    import serial.tools.list_ports
    usb_support = True
except:
    usb_support = False

try:
    from bluepy.btle import Scanner, DefaultDelegate, Peripheral
    ble_support = True
except:
    ble_support = False


class MillenniumChess:
    def __init__(self, rescan=False, verbose=False):
        self.replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.verbose = verbose
        if usb_support is False and ble_support is False:
            print(
                "You need to either install pyserial or bluepy, currently no transport is available.")
            return

        scan = False
        self.mill_config = None

        if rescan is False:
            try:
                with open("millennium_config.json", "r") as f:
                    self.mill_config = json.load(f)
            except:
                scan = True
        else:
            scan = True

        if scan is True and ble_support is True:
            bledev = self.ble_scan()
            if bledev is not None:
                self.mill_config = {"connection": "ble", "address": bledev}
                scan = False  # Don't look for USB, we found BLE.

        if scan is True and usb_support is True:
            usbdev = self.usb_scan()
            if usbdev is not None:
                self.mill_config = {"connection": "usb", "address": usbdev}

        if scan is True and self.mill_config is not None:
            try:
                with open("millennium_config.json", "w") as f:
                    json.dump(self.mill_config, f)
            except:
                if self.verbose:
                    print("Failed to save connection configuration {} to {}".format(
                        self.mill_config, "millennium_config.json"))
            scan = False

    def ble_scan(self):
        class ScanDelegate(DefaultDelegate):
            def __init__(self, verbose=False):
                self.verbose = verbose
                DefaultDelegate.__init__(self)

            def handleDiscovery(self, dev, isNewDev, isNewData):
                if isNewDev:
                    if self.verbose is True:
                        print("Discovered device {}".format(dev.addr))
                elif isNewData:
                    if self.verbose is True:
                        print("Received new data from {}".format(dev.addr))

        scanner = Scanner().withDelegate(ScanDelegate(self.verbose))

        try:
            devices = scanner.scan(10.0)
        except:
            print(
                "BLE scanning failed. You might need to excecute the scan with root rights.")
            return None

        for bledev in devices:
            if self.verbose is True:
                print("Device {} ({}), RSSI={} dB".format(
                    bledev.addr, bledev.addrType, bledev.rssi))
            for (adtype, desc, value) in bledev.getScanData():
                if self.verbose is True:
                    print("  {} ({}) = {}".format(desc, adtype, value))
                if desc == "Complete Local Name":
                    if "MILLENNIUM CHESS" in value:
                        if self.verbose is True:
                            print(
                                "Autodetected Millennium board at Bluetooth LE address: {}".format(bledev))
                        return bledev
        return None

    def usb_scan(self):
        port = None
        ports = self.usb_port_search()
        if len(ports) > 0:
            if self.verbose:
                if len(ports) > 1:
                    print("Found {} Millennium boards.".format(len(ports)))
            port = ports[0]
            if self.verbose is True:
                print("Autodetected Millennium board at USB port: {}".format(port))
        return port

    def usb_version_quick_check(self, port):
        try:
            if self.verbose is True:
                print("Testing port: {}".format(port))
            usbdev = serial.Serial(port, 38400, timeout=2)
            usbdev.dtr = 0
            self.usb_write(usbdev, "V")
            version = self.usb_read_synchr(usbdev, 'v', 7)
            if len(version) != 7:
                usbdev.close()
                if self.verbose is True:
                    print("Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                if self.verbose is True:
                    print("Unexpected reply {}".format(version))
                usbdev.close()
                return None
            version = '{}.{}'.format(version[1:2], version[3:4])
            if self.verbose is True:
                print("Millennium {} at {}", version, port)
            usbdev.close()
            return version
        except (OSError, serial.SerialException):
            pass
        usbdev.close()
        return None

    def usb_port_check(self, port):
        try:
            if self.verbose:
                print("Testing port: {}".format(port))
            s = serial.Serial(port, 38400)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            if self.verbose:
                print("Can't open port {}, {}".format(port, e))
            return False

    def usb_port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.usb_port_check(port):
                version = self.usb_version_quick_check(port)
                if version != None:
                    if self.verbose:
                        print("Found board at: {}".format(port))
                    vports.append(port)
        return vports

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

    def hex2(self, num):
        d1 = num//16
        d2 = num % 16
        s = self.hexd(d1)+self.hexd(d2)
        return s

    def usb_write(self, usbdev, msg):
        try:
            usbdev.reset_output_buffer()
            usbdev.reset_input_buffer()
        except (Exception) as e:
            if self.verbose:
                print("Failed to empty read-buffer: {}", e)
        gpar = 0
        for b in msg:
            gpar = gpar ^ ord(b)
        msg = msg+self.hex2(gpar)
        bts = []
        for c in msg:
            bo = self.add_odd_par(c)
            bts.append(bo)
        try:
            usbdev.write(bts)
            usbdev.flush()
        except (Exception) as e:
            if self.verbose:
                print("Failed to write {}: {}", msg, e)

    def usb_read_synchr(self, usbdev, cmd, num):
        rep = []
        start = False
        while start is False:
            try:
                b = chr(ord(usbdev.read()) & 127)
            except:
                return []
            if b == cmd:
                rep.append(b)
                start = True
        for _ in range(num-1):
            try:
                b = chr(ord(usbdev.read()) & 127)
                rep.append(b)
            except (Exception) as e:
                if self.verbose:
                    print("Read error {}".format(e))
                break
        if len(rep) > 2:
            gpar = 0
            for b in rep[:-2]:
                gpar = gpar ^ ord(b)
            if rep[-2]+rep[-1] != self.hex2(gpar):
                if self.verbose:
                    print("CRC error rep={} CRCs: {}!={}".format(rep,
                                                                 ord(rep[-2]), self.hex2(gpar)))
                return []
        return rep

    def usb_open(self, port):
        if port and port != "":
            if self.usb_port_check(port):
                try:
                    self.usb_port = serial.Serial(port, 38400)  # , timeout=1)
                    self.usb_port.dtr = 0
                    self.init = True
                except (OSError, serial.SerialException) as e:
                    if self.verbose is True:
                        print("Can't open port {}, {}".format(port, e))
                    self.init = False
            else:
                if self.verbose is True:
                    print("Invalid port {}".format(port))
                self.init = False
        else:
            if self.verbose is True:
                print("No port found.")
            self.init = False


if __name__ == "__main__":
    mlb = MillenniumChess(rescan=True, verbose=True)
