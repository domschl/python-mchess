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

        logging.error("USB not implemented")
        self.init = False

    def start(self, port):
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
