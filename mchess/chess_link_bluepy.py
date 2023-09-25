"""
ChessLink transport implementation for Bluetooth LE connections using `bluepy`.
"""
import logging
import threading
import queue
import time
import os

import chess_link_protocol as clp
try:
    import bluepy
    from bluepy.btle import Scanner, DefaultDelegate, Peripheral
    bluepy_ble_support = True
except ImportError:
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
        if bluepy_ble_support is False:
            self.init = False
            return
        self.wrque = queue.Queue()
        self.log = logging.getLogger("ChessLinkBluePy")
        self.que = que  # asyncio.Queue()
        self.init = True
        self.log.debug("bluepy_ble init ok")
        self.protocol_debug = protocol_dbg
        self.scan_timeout = 10
        self.worker_thread_active = False
        self.worker_threader = None
        self.conn_state = None

        self.bp_path = os.path.dirname(os.path.abspath(bluepy.__file__))
        self.bp_helper = os.path.join(self.bp_path, 'bluepy-helper')
        if not os.path.exists(self.bp_helper):
            self.log.warning(f'Unexpected: {self.bp_helper} does not exists!')
        self.fix_cmd = "sudo setcap 'cap_net_raw,cap_net_admin+eip' " + self.bp_helper

    def quit(self):
        """
        Initiate worker-thread stop
        """
        self.worker_thread_active = False

    def search_board(self, iface=0):
        """
        Search for ChessLink connections using Bluetooth LE.

        :param iface: interface number of bluetooth adapter, default 1.
        :returns: Bluetooth address of ChessLink board, or None on failure.
        """
        self.log.debug("bluepy_ble: searching for boards")

        class ScanDelegate(DefaultDelegate):
            ''' scanner class '''

            def __init__(self, log):
                self.log = log
                DefaultDelegate.__init__(self)

            def handleDiscovery(self, scanEntry, isNewDev, isNewData):
                if isNewDev:
                    self.log.debug(
                        "Discovered device {}".format(scanEntry.addr))
                elif isNewData:
                    self.log.debug(
                        "Received new data from {}".format(scanEntry.addr))

        scanner = Scanner(iface=iface).withDelegate(ScanDelegate(self.log))

        try:
            devices = scanner.scan(self.scan_timeout)
        except Exception as e:
            self.log.error(f"BLE scanning failed. {e}")
            self.log.error(f"excecute: {self.fix_cmd}")
            self.log.error("or (if that fails) start ONCE with: `sudo python mchess.py`"
                           "(fix ownership of chess_link_config.json afterwards)")
            return None

        devs = sorted(devices, key=lambda x: x.rssi, reverse=True)
        for b in devs:
            self.log.debug(f'sorted by rssi {b.addr} {b.rssi}')

        for bledev in devs:
            self.log.debug(
                f"Device {bledev.addr} ({bledev.addrType}), RSSI={bledev.rssi} dB")
            for (adtype, desc, value) in bledev.getScanData():
                self.log.debug(f"  {desc} ({adtype}) = {value}")
                if desc == "Complete Local Name":
                    if "MILLENNIUM CHESS" in value:
                        self.log.info("Autodetected Millennium Chess Link board at "
                                      f"Bluetooth LE address: {bledev.addr}, "
                                      f"signal strength (rssi): {bledev.rssi}")
                        return bledev.addr
        return None

    def test_board(self, address):
        """
        Test dummy.

        :returns: Version string "1.0" always.
        """
        self.log.debug(f"test_board address {address} not implemented.")
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
        while self.conn_state is None and time.time() - timer < 5.0:
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
            self.log.debug(f'write-que-entry {msg}')
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
        que.put('agent-state: ' + state + ' ' + msg)

    def mil_open(self, address, mil, que, log):

        class PeriDelegate(DefaultDelegate):
            ''' peripheral delegate class '''

            def __init__(self, log, que):
                self.log = log
                self.que = que
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
                        rxh + 1, (1).to_bytes(2, byteorder='little'))
                if chri.uuid == "49535343-8841-43f4-a8d4-ecbe34729bb3":  # RX char, tx for us
                    tx = chri
                    # txh = chri.getHandle()
                if chri.supportsRead():
                    log.debug(f"  {chri} UUID={chri.uuid} {chri.propertiesToString()} -> "
                              "{chri.read()}")
                else:
                    log.debug(
                        f"  {chri} UUID={chri.uuid}{chri.propertiesToString()}")

        try:
            log.debug('Installing peripheral delegate')
            delegate = PeriDelegate(log, que)
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

        time_last_out = time.time() + 0.2

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
                            f"Reconnect failed: {e} [Local bluetooth problem?]")
                        rep_err = True
                    bt_error = True
                if bt_error is False:
                    self.log.info(f"Bluetooth reconnected to {address}")
                    rx, tx = self.mil_open(address, mil, que, log)
                    time_last_out = time.time() + 0.2
                    self.init = True

            if wrque.empty() is False and time.time() - time_last_out > message_delta_time:
                msg = wrque.get()
                gpar = 0
                for b in msg:
                    gpar = gpar ^ ord(b)
                msg = msg + clp.hex2(gpar)
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
                    log.error(f"bluepy_ble: failed to write {msg}: {e}")
                    bt_error = True
                    self.agent_state(
                        que, 'offline', f'Connected to Bluetooth peripheral lost: {e}')
                wrque.task_done()

            try:
                rx.read()
                mil.waitForNotifications(0.05)
                # time.sleep(0.1)
            except Exception as e:
                self.log.warning(f"Bluetooth error {e}")
                bt_error = True
                self.agent_state(
                    que, 'offline', f'Connected to Bluetooth peripheral lost: {e}')
                continue

        log.debug('wt-end')
