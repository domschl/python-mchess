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
            'millcon_bluepy_ble', 'millcon_usb']}

        if sys.version_info[0] < 3:
            logging.critical("FATAL: You need Python 3.x to run this module.")
            exit(-1)

        if platform.system() not in self.transports:
            logging.critical(
                "Fatal: {} is not a supported platform.".format(platform.system()))
            msg = "Supported are: "
            for p in self.transports:
                msg += '{} '.format(p)
            logging.info(msg)
            exit(-1)

        self.trans = None
        self.que = queue.Queue()  # asyncio.Queue()
        self.mill_config = None
        found_board = False

        try:
            with open("millennium_config.json", "r") as f:
                self.mill_config = json.load(f)
                logging.debug('Checking default configuration for board via {} at {}'.format(
                    self.mill_config['transport'], self.mill_config['address']))
                trans = self._open_transport(self.mill_config['transport'])
                if trans is not None:
                    if trans.test_board(self.mill_config['address']) is not None:
                        logging.debug('Default board operational.')
                        found_board = True
                        self.trans = trans
                    else:
                        logging.warning(
                            'Default board not available, start scan.')
                        self.mill_config = None
        except Exception as e:
            self.mill_config = None
            logging.debug(
                'No valid default configuration, starting board-scan: {}'.format(e))

        if found_board is False:
            address = None
            for transport in self.transports[platform.system()]:
                try:
                    tri = importlib.import_module(transport)
                    logging.debug("imported {}".format(transport))
                    tr = tri.Transport(self.que)
                    logging.debug("created obj")
                    if tr.is_init() is True:
                        logging.debug(
                            "Transport {} loaded.".format(tr.get_name()))
                        address = tr.search_board()
                        if address is not None:
                            logging.info("Found board on transport {} at address {}".format(
                                tr.get_name(), address))
                            self.mill_config = {
                                'transport': tr.get_name(), 'address': address}
                            self.trans = tr
                            try:
                                with open("millennium_config.json", "w") as f:
                                    json.dump(self.mill_config, f)
                            except Exception as e:
                                logging.error("Failed to save default configuration {} to {}: {}".format(
                                    self.mill_config, "millennium_config.json", e))
                            break
                    else:
                        logging.warning("Transport {} failed to initialize".format(
                            tr.get_name()))
                except Exception as e:
                    logging.warning("Internal error, import of {} failed: {}".format(
                        transport, e))

        if self.mill_config is None:
            logging.error(
                "No transport available, cannot connect.")
            return
        else:
            logging.info('Valid board available on {} at {}'.format(
                self.mill_config['transport'], self.mill_config['address']))
            if os.geteuid() == 0:
                logging.warning(
                    'Do not run as root, once intial BLE scan is done.')
            self.trans.open_mt(self.mill_config['address'])

    def _open_transport(self, transport):
        try:
            tri = importlib.import_module(transport)
            logging.debug("imported {}".format(transport))
            tr = tri.Transport(self.que)
            logging.debug("created obj")
            if tr.is_init() is True:
                logging.debug("Transport {} loaded.".format(tr.get_name()))
                return tr
            else:
                logging.warning("Transport {} failed to initialize".format(
                    tr.get_name()))
        except:
            logging.warning("Internal error, import of {} failed, transport not available.".format(
                transport))
        return None

    def get_version(self):
        version = ""
        self.trans.write_mt("V")
        repl = self.que.get()
        logging.debug("Reply: {}".format(repl))
        if repl[0] != 'v':
            logging.error(
                "We are currently not correctly handling out-of-order replies!")
        else:
            version = '{}.{}'.format(repl[1]+repl[2], repl[3]+repl[4])
            return version
        return '?'


# async def testme():
#     await


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    brd = MillenniumChess()
    brd.get_version()
    while True:
        brd.trans.mil.waitForNotifications(1.0)
    time.sleep(100)
   #  testme()
