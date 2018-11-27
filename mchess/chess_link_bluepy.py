"""
ChessLink transport implementation for Bluetooth LE connections using `bluepy`.
"""
import logging
import threading
import queue
import time

import chess_link_protocol as clp
try:
    from bluepy.btle import Scanner, DefaultDelegate, Peripheral
    bluepy_ble_support = True
except:
    bluepy_ble_support = False


class Transport():
    """
    ChessLink transport implementation for Bluetooth LE connections using `bluepy`.

    This class does automatic hardware detection of any ChessLink board using bluetooth LE
    and supports Linux and Raspberry Pi.

    This transport uses an asynchronous background thread for hardware communcation.
    All replies are written to the python queue `que` given during initialization.

    For the details of the Chess Link protocol, please refer to: 
    `magic-link.md <https://github.com/domschl/python-mchess/blob/master/mchess/magic-board.md>`_.
    """

    def __init__(self, que, protocol_dbg=False):
        """
        Initialize with python queue for event handling.
        Events are strings conforming to the ChessLink protocol as documented in 
        `magic-link.md <https://github.com/domschl/python-mchess/blob/master/mchess/magic-board.md>`_.

        :param que: Python queue that will eceive events from chess board.
        :param protocol_dbg: True: byte-level ChessLink protocol debug messages
        """
        if bluepy_ble_support == False:
            self.init = False
            return
        self.wrque = queue.Queue()
        self.log = logging.getLogger("ChessLinkBluePy")
        self.que = que  # asyncio.Queue()
        self.init = True
        self.log.debug("bluepy_ble init ok")
        self.protocol_debug = protocol_dbg

    def quit(self):
        """
        Initiate worker-thread stop
        """
        self.worker_thread_active = False

    def search_board(self):
        """
        Search for ChessLink connections using Bluetooth LE.

        :returns: Bluetooth address of ChessLink board, or None on failure.
        """
        self.log.debug("bluepy_ble: searching for boards")

        class ScanDelegate(DefaultDelegate):
            def __init__(self, log):
                self.log = log
                DefaultDelegate.__init__(self)

            def handleDiscovery(self, dev, isNewDev, isNewData):
                if isNewDev:
                    self.log.debug("Discovered device {}".format(dev.addr))
                elif isNewData:
                    self.log.debug(
                        "Received new data from {}".format(dev.addr))

        scanner = Scanner().withDelegate(ScanDelegate(self.log))

        try:
            devices = scanner.scan(10.0)
        except Exception as e:
            self.log.error(
                "BLE scanning failed. You might need to excecute the scan with root rights: {}".format(e))
            return None

        devs = sorted(devices, key=lambda x: x.rssi, reverse=True)
        print("Sorted:")
        for b in devs:
            self.log.debug('sorted by rssi {} {}'.format(b.addr, b.rssi))

        for bledev in devs:
            self.log.debug("Device {} ({}), RSSI={} dB".format(
                bledev.addr, bledev.addrType, bledev.rssi))
            for (adtype, desc, value) in bledev.getScanData():
                self.log.debug("  {} ({}) = {}".format(desc, adtype, value))
                if desc == "Complete Local Name":
                    if "MILLENNIUM CHESS" in value:
                        self.log.info(
                            "Autodetected Millennium Chess Link board at Bluetooth LE address: {}, signal strength (rssi): {}".format(
                                bledev.addr, bledev.rssi))
                        return bledev.addr
        return None

    def test_board(self, address):
        """
        Test dummy.

        :returns: Version string "1.0" always.
        """
        # self.open_mt(address)
        return "1.0"

    def open_mt(self, address):
        """
        Open a bluetooth LE connection to ChessLink board.

        :param address: bluetooth address
        :returns: True on success.
        """
        self.log.debug('Starting worker-thread for bluepy ble')
        self.worker_thread_active = True
        self.worker_threader = threading.Thread(
            target=self.worker_thread, args=(self.log, address, self.wrque, self.que))
        self.worker_threader.setDaemon(True)
        self.worker_threader.start()
        timer = time.time()
        self.conn_state = None
        while self.conn_state is None and time.time()-timer < 5.0:
            time.sleep(0.1)
        if self.conn_state is None:
            return False
        return self.conn_state

    def write_mt(self, msg):
        """
        Encode and asynchronously write a message to ChessLink.

        :param msg: Message string. Parity will be added, and block CRC appended.
        """
        if self.protocol_debug is True:
            self.log.debug('write-que-entry {}'.format(msg))
        self.wrque.put(msg)

    def get_name(self):
        """
        Get name of this transport.

        :returns: 'chess_link_bluepy'
        """
        return "chess_link_bluepy"

    def is_init(self):
        """
        Check, if hardware connection is up.

        :returns: True on success.
        """
        return self.init

    def agent_state(self, que, state, msg):
        que.put('agent-state: '+state + ' ' + msg)

    def mil_open(self, address, mil, que, log):

        class PeriDelegate(DefaultDelegate):
            def __init__(self, log, que):
                self.log = log
                self.log.debug("Init delegate for peri")
                self.chunks = ""
                DefaultDelegate.__init__(self)

            def handleNotification(self, cHandle, data):
                self.log.debug(
                    "BLE: Handle: {}, data: {}".format(cHandle, data))
                rcv = ""
                for b in data:
                    rcv += chr(b & 127)
                self.log.debug('BLE received [{}]'.format(rcv))
                self.chunks += rcv
                if self.chunks[0] not in clp.protocol_replies:
                    self.log.warning(
                        "Illegal reply start '{}' received, discarding".format(self.chunks[0]))
                    while len(self.chunks) > 0 and self.chunks[0] not in clp.protocol_replies:
                        self.chunks = self.chunks[1:]
                if len(self.chunks) > 0:
                    mlen = clp.protocol_replies[self.chunks[0]]
                    if len(self.chunks) >= mlen:
                        valmsg = self.chunks[:mlen]
                        self.log.debug(
                            'bluepy_ble received complete msg: {}'.format(valmsg))
                        if clp.check_block_crc(valmsg):
                            que.put(valmsg)
                        self.chunks = self.chunks[mlen:]

        rx = None
        tx = None
        log.debug('Peripheral generated {}'.format(address))
        try:
            services = mil.getServices()
        except Exception as e:
            emsg = 'Failed to enumerate services for {}, {}'.format(address, e)
            log.error(emsg)
            self.agent_state(que, 'offline', emsg)
            return None, None
        # time.sleep(0.1)
        log.debug("services: {}".format(len(services)))
        for ser in services:
            log.debug('Service: {}'.format(ser))
            chrs = ser.getCharacteristics()
            for chri in chrs:
                if chri.uuid == "49535343-1e4d-4bd9-ba61-23c647249616":  # TX char, rx for us
                    rx = chri
                    rxh = chri.getHandle()
                    # Enable notification magic:
                    log.debug('Enabling notifications')
                    mil.writeCharacteristic(
                        rxh+1, (1).to_bytes(2, byteorder='little'))
                if chri.uuid == "49535343-8841-43f4-a8d4-ecbe34729bb3":  # RX char, tx for us
                    tx = chri
                    # txh = chri.getHandle()
                if chri.supportsRead():
                    log.debug("  {} UUID={} {} -> {}".format(chri, chri.uuid,
                                                             chri.propertiesToString(), chri.read()))
                else:
                    log.debug("  {} UUID={}{}".format(
                        chri, chri.uuid, chri.propertiesToString()))

        try:
            log.debug('Installing peripheral delegate')
            delegate = PeriDelegate(log, que)
            delegate.que = que
            mil.withDelegate(delegate)
        except Exception as e:
            emsg = 'Bluetooth LE: Failed to install peripheral delegate! {}'.format(
                e)
            log.error(emsg)
            self.agent_state(que, 'offline', emsg)
            return None, None
        self.agent_state(que, 'online', 'Connected to ChessLink board via BLE')
        return (rx, tx)

    def worker_thread(self, log, address, wrque, que):
        """
        Background thread that handles bluetooth sending and forwards data received via 
        bluetooth to the queue `que`.
        """
        mil = None
        message_delta_time = 0.1  # least 0.1 sec between outgoing btle messages

        rx = None
        tx = None
        log.debug("bluepy_ble open_mt {}".format(address))
        # time.sleep(0.1)
        try:
            log.debug("per1")
            mil = Peripheral(address)
            log.debug("per2")
        except Exception as e:
            log.debug("per3")
            emsg = 'Failed to create BLE peripheral at {}, {}'.format(
                address, e)
            log.error(emsg)
            self.agent_state(que, 'offline', '{}'.format(e))
            self.conn_state = False
            return

        rx, tx = self.mil_open(address, mil, que, log)

        time_last_out = time.time()+0.2

        if rx is None or tx is None:
            bt_error = True
            self.conn_state = False
        else:
            bt_error = False
            self.conn_state = True
        while self.worker_thread_active is True:
            rep_err = False
            while bt_error is True:
                time.sleep(1)
                bt_error = False
                self.init = False
                try:
                    mil.connect(address)
                except Exception as e:
                    if rep_err is False:
                        self.log.warning(
                            "Reconnect failed: {} [Local bluetooth problem?]".format(e))
                        rep_err = True
                    bt_error = True
                if bt_error is False:
                    self.log.info(
                        "Bluetooth reconnected to {}".format(address))
                    rx, tx = self.mil_open(address, mil, que, log)
                    time_last_out = time.time()+0.2
                    self.init = True

            if wrque.empty() is False and time.time()-time_last_out > message_delta_time:
                msg = wrque.get()
                gpar = 0
                for b in msg:
                    gpar = gpar ^ ord(b)
                msg = msg+clp.hex2(gpar)
                if self.protocol_debug is True:
                    log.debug("blue_ble write: <{}>".format(msg))
                bts = ""
                for c in msg:
                    bo = chr(clp.add_odd_par(c))
                    bts += bo
                    btsx = bts.encode('latin1')
                if self.protocol_debug is True:
                    log.debug("Sending: <{}>".format(btsx))
                try:
                    tx.write(btsx, withResponse=True)
                    time_last_out = time.time()
                except Exception as e:
                    log.error(
                        "bluepy_ble: failed to write {}: {}".format(msg, e))
                    bt_error = True
                    self.agent_state(
                        que, 'offline', 'Connected to Bluetooth peripheral lost: {}'.format(e))
                wrque.task_done()

            try:
                rx.read()
                mil.waitForNotifications(0.05)
                # time.sleep(0.1)
            except Exception as e:
                self.log.warning("Bluetooth error {}".format(e))
                bt_error = True
                self.agent_state(
                    que, 'offline', 'Connected to Bluetooth peripheral lost: {}'.format(e))
                continue

        log.debug('wt-end')
