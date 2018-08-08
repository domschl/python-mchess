import time
import logging
import os
import platform
import sys
import struct
import threading
import asyncio
import queue
import json
import importlib

try:
    import chess
    import chess.uci
    chess_support = True
except:
    chess_support = False


class MillenniumChess:
    def __init__(self):
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.transports = {'Darwin': ['millcon_usb', 'millcon_bluepy_ble'], 'Linux': [
            'millcon_bluepy_ble', 'millcon_usb'], 'Windows': ['millcon_usb']}

        self.log = logging.getLogger('Millenium')
        self.log.info("Millenium starting")
        if sys.version_info[0] < 3:
            self.log.critical("FATAL: You need Python 3.x to run this module.")
            exit(-1)

        if platform.system() not in self.transports:
            self.log.critical(
                "Fatal: {} is not a supported platform.".format(platform.system()))
            msg = "Supported are: "
            for p in self.transports:
                msg += '{} '.format(p)
            self.log.info(msg)
            exit(-1)

        self.trans = None
        self.que = queue.Queue()  # asyncio.Queue()
        self.mill_config = None
        self.connected = False
        found_board = False

        try:
            with open("millennium_config.json", "r") as f:
                self.mill_config = json.load(f)
                self.log.debug('Checking default configuration for board via {} at {}'.format(
                    self.mill_config['transport'], self.mill_config['address']))
                trans = self._open_transport(self.mill_config['transport'])
                if trans is not None:
                    if trans.test_board(self.mill_config['address']) is not None:
                        self.log.debug('Default board operational.')
                        found_board = True
                        self.trans = trans
                    else:
                        self.log.warning(
                            'Default board not available, start scan.')
                        self.mill_config = None
        except Exception as e:
            self.mill_config = None
            self.log.debug(
                'No valid default configuration, starting board-scan: {}'.format(e))

        if found_board is False:
            address = None
            for transport in self.transports[platform.system()]:
                try:
                    tri = importlib.import_module(transport)
                    self.log.debug("imported {}".format(transport))
                    tr = tri.Transport(self.que)
                    self.log.debug("created obj")
                    if tr.is_init() is True:
                        self.log.debug(
                            "Transport {} loaded.".format(tr.get_name()))
                        address = tr.search_board()
                        if address is not None:
                            self.log.info("Found board on transport {} at address {}".format(
                                tr.get_name(), address))
                            self.mill_config = {
                                'transport': tr.get_name(), 'address': address}
                            self.trans = tr
                            try:
                                with open("millennium_config.json", "w") as f:
                                    json.dump(self.mill_config, f)
                            except Exception as e:
                                self.log.error("Failed to save default configuration {} to {}: {}".format(
                                    self.mill_config, "millennium_config.json", e))
                            break
                    else:
                        self.log.warning("Transport {} failed to initialize".format(
                            tr.get_name()))
                except Exception as e:
                    self.log.warning("Internal error, import of {} failed: {}".format(
                        transport, e))

        if self.mill_config is None or self.trans is None:
            self.log.error(
                "No transport available, cannot connect.")
            return
        else:
            self.log.info('Valid board available on {} at {}'.format(
                self.mill_config['transport'], self.mill_config['address']))
            if platform.system() != 'Windows':
                if os.geteuid() == 0:
                    self.log.warning(
                        'Do not run as root, once intial BLE scan is done.')
            self.connected = self.trans.open_mt(self.mill_config['address'])

    def _open_transport(self, transport):
        try:
            tri = importlib.import_module(transport)
            self.log.debug("imported {}".format(transport))
            tr = tri.Transport(self.que)
            self.log.debug("created obj")
            if tr.is_init() is True:
                self.log.debug("Transport {} loaded.".format(tr.get_name()))
                return tr
            else:
                self.log.warning("Transport {} failed to initialize".format(
                    tr.get_name()))
        except:
            self.log.warning("Internal error, import of {} failed, transport not available.".format(
                transport))
        return None

    def get_version(self):
        version = ""
        self.trans.write_mt("V")
        repl = self.que.get()
        self.log.debug("Reply: {}".format(repl))
        if repl[0] != 'v':
            self.log.error(
                "We are currently not correctly handling out-of-order replies!")
        else:
            version = '{}.{}'.format(repl[1]+repl[2], repl[3]+repl[4])
            return version
        return '?'


# async def testme():
#     await


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG)
    brd = MillenniumChess()
    if brd.connected is True:
        brd.get_version()
        while True:
            pass
            # brd.trans.mil.waitForNotifications(1.0)
        time.sleep(100)
   #  testme()
