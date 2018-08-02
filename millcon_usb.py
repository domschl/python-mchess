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
        self.que = que  # asyncio.Queue()
        self.init = True
        logging.debug("USB init ok")

    def search_board(self):
        logging.debug("USB: search for boards")
        port = None
        ports = self.usb_port_search()
        if len(ports) > 0:
            if len(ports) > 1:
                logging.warning(
                    "Found {} Millennium boards, using first found.".format(len(ports)))
            port = ports[0]
            logging.info(
                "Autodetected Millennium board at USB port: {}".format(port))
        return port

    def test_board(self, port):
        logging.debug("Testing port: {}".format(port))
        try:
            usbdev = serial.Serial(port, 38400, timeout=2)
            usbdev.dtr = 0
            self.write(usbdev, "V")
            version = self.usb_read_synchr(usbdev, 'v', 7)
            if len(version) != 7:
                usbdev.close()
                logging.debug(
                    "Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                logging.debug("Unexpected reply {}".format(version))
                usbdev.close()
                return None
            version = '{}.{}'.format(version[1:2], version[3:4])
            logging.debug("Millennium {} at {}".format(version, port))
            usbdev.close()
            return version
        except (OSError, serial.SerialException) as e:
            logging.debug(
                'Board detection on {} resulted in error {}'.format(port, e))
        try:
            usbdev.close()
        except Exception:
            pass
        return None

    def usb_port_check(self, port):
        logging.debug("Testing port: {}".format(port))
        try:
            s = serial.Serial(port, 38400)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            logging.debug("Can't open port {}, {}".format(port, e))
            return False

    def usb_port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.usb_port_check(port):
                version = self.test_board(port)
                if version != None:
                    logging.info("Found board at: {}".format(port))
                    vports.append(port)
        return vports

    def write(self, usbdev, msg):
        gpar = 0
        for b in msg:
            gpar = gpar ^ ord(b)
        msg = msg+mill_prot.hex2(gpar)
        bts = []
        for c in msg:
            bo = mill_prot.add_odd_par(c)
            bts.append(bo)
        try:
            usbdev.write(bts)
            usbdev.flush()
        except Exception as e:
            logging.error("Failed to write {}: {}".format(msg, e))

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
                logging.error("Read error {}".format(e))
                break
        if len(rep) > 2:
            gpar = 0
            for b in rep[:-2]:
                gpar = gpar ^ ord(b)
            if rep[-2]+rep[-1] != mill_prot.hex2(gpar):
                logging.warning("CRC error rep={} CRCs: {}!={}".format(rep,
                                                                       ord(rep[-2]), mill_prot.hex2(gpar)))
                return []
        return rep

    def open(self, port):
        try:
            self.usb_dev = serial.Serial(port, 38400)  # , timeout=1)
            self.usb_dev.dtr = 0
        except Exception as e:
            logging.error('USB cannot open port {}, {}'.format(port, e))
            return False
        self.thread_active = True
        self.event_thread = threading.Thread(
            target=self.event_worker_thread, args=(self.usb_dev, self.que))
        self.event_thread.setDaemon(True)
        self.event_thread.start()

    def event_worker_thread(self, usb_dev, que):
        cmd_started = False
        cmd_size = 0
        cmd = ""
        while self.thread_active:
            try:
                if cmd_started == False:
                    usb_dev.timeout = 0
                else:
                    usb_dev.timeout = 2
                b = chr(ord(self.usb_dev.read()) & 127)
            except Exception as e:
                if len(cmd) > 0:
                    logging.debug(
                        "USB command '{}' interrupted: {}".format(cmd[0], e))
                time.sleep(0.1)
                cmd_started = False
                cmd_size = 0
                cmd = ""
                pass
            if cmd_started is False:
                if b in mill_prot.millennium_protocol_replies:
                    cmd_started = True
                    cmd_size = mill_prot.millennium_protocol_replies[b]
                    cmd = b
            else:
                cmd += b
                cmd_size -= 1
                if cmd_size == 0:
                    cmd_started = False
                    cmd_size = 0
                    logging.debug("USB received cmd: {}".format(cmd))
                    que.put(cmd)
                    cmd = ""

    def get_name(self):
        return "millcon_usb"

    def is_init(self):
        logging.debug("Ask for init")
        return self.init
