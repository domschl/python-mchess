import logging
import threading
import queue
import time

import mill_prot

try:
    import serial
    import serial.tools.list_ports
    usb_support = True
except:
    usb_support = False


class Transport():
    def __init__(self, que):
        if usb_support == False:
            self.init = False
            return
        self.log = logging.getLogger("MillenniumUSB")
        self.que = que  # asyncio.Queue()
        self.init = True
        self.log.debug("USB init ok")

    def search_board(self):
        self.log.debug("USB: searching for boards")
        port = None
        ports = self.usb_port_search()
        if len(ports) > 0:
            if len(ports) > 1:
                self.log.warning(
                    "Found {} Millennium boards, using first found.".format(len(ports)))
            port = ports[0]
            self.log.info(
                "Autodetected Millennium board at USB port: {}".format(port))
        return port

    def test_board(self, port):
        self.log.debug("Testing port: {}".format(port))
        try:
            self.usb_dev = serial.Serial(port, 38400, timeout=2)
            self.usb_dev.dtr = 0
            self.write_mt("V")
            version = self.usb_read_synchr(self.usb_dev, 'v', 7)
            if len(version) != 7:
                self.usb_dev.close()
                self.log.debug(
                    "Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                self.log.debug("Unexpected reply {}".format(version))
                self.usb_dev.close()
                return None
            verstring = '{}.{}'.format(
                version[1]+version[2], version[3]+version[4])
            self.log.debug("Millennium {} at {}".format(verstring, port))
            self.usb_dev.close()
            return verstring
        except (OSError, serial.SerialException) as e:
            self.log.debug(
                'Board detection on {} resulted in error {}'.format(port, e))
        try:
            self.usb_dev.close()
        except Exception:
            pass
        return None

    def usb_port_check(self, port):
        self.log.debug("Testing port: {}".format(port))
        try:
            s = serial.Serial(port, 38400)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            self.log.debug("Can't open port {}, {}".format(port, e))
            return False

    def usb_port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.usb_port_check(port):
                version = self.test_board(port)
                if version != None:
                    self.log.debug("Found board at: {}".format(port))
                    vports.append(port)
                    break  # only one port necessary
        return vports

    def write_mt(self, msg):
        msg = mill_prot.add_block_crc(msg)
        bts = []
        for c in msg:
            bo = mill_prot.add_odd_par(c)
            bts.append(bo)
        try:
            self.log.debug('Trying write <{}>'.format(bts))
            self.usb_dev.write(bts)
            self.usb_dev.flush()
        except Exception as e:
            self.log.error("Failed to write {}: {}".format(msg, e))
            return False
        self.log.debug("Written '{}' as < {} > ok".format(msg, bts))
        return True

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
                self.log.error("Read error {}".format(e))
                break
        if mill_prot.check_block_crc(rep) is False:
            return []
        return rep

    def open_mt(self, port):
        try:
            self.usb_dev = serial.Serial(port, 38400, timeout=0.1)
            self.usb_dev.dtr = 0
        except Exception as e:
            self.log.error('USB cannot open port {}, {}'.format(port, e))
            return False
        self.log.debug('USB port {} open'.format(port))
        self.thread_active = True
        self.event_thread = threading.Thread(
            target=self.event_worker_thread, args=(self.usb_dev, self.que))
        self.event_thread.setDaemon(True)
        self.event_thread.start()
        return True

    def event_worker_thread(self, usb_dev, que):
        self.log.debug('USB worker thread started.')
        cmd_started = False
        cmd_size = 0
        cmd = ""
        while self.thread_active:
            b = ""
            # time.sleep(0.2)
            try:
                if cmd_started == False:
                    self.usb_dev.timeout = None
                else:
                    self.usb_dev.timeout = 0.2
                by = self.usb_dev.read()
                if len(by) > 0:
                    b = chr(ord(by) & 127)
                else:
                    continue
            except Exception as e:
                if len(cmd) > 0:
                    self.log.debug(
                        "USB command '{}' interrupted: {}".format(cmd[0], e))
                time.sleep(0.1)
                cmd_started = False
                cmd_size = 0
                cmd = ""
                continue
            if len(b) > 0:
                if cmd_started is False:
                    if b in mill_prot.millennium_protocol_replies:
                        cmd_started = True
                        cmd_size = mill_prot.millennium_protocol_replies[b]
                        cmd = b
                        cmd_size -= 1
                else:
                    cmd += b
                    cmd_size -= 1
                    if cmd_size == 0:
                        cmd_started = False
                        cmd_size = 0
                        self.log.debug("USB received cmd: {}".format(cmd))
                        if mill_prot.check_block_crc(cmd):
                            que.put(cmd)
                        cmd = ""

    def get_name(self):
        return "millcon_usb"

    def is_init(self):
        self.log.debug("Ask for init")
        return self.init
