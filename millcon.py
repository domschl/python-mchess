import time
import logging
import os
import platform
import sys
import struct
import threading
import asyncio
import json
import importlib

try:
    import chess
    import chess.uci
    chess_support = True
except:
    chess_support = False


class MillenniumChess:
    def __init__(self, rescan=False, verbose=False):
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.transports = {'Darwin': ['millcon_usb', 'millcon_bluepy_ble'], 'Linux': [
            'millcon_bluepy_ble', 'millcon_usb']}
        self.verbose = verbose

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

        trans = []
        self.que = asyncio.Queue()

        for transport in self.transports[platform.system()]:
            try:
                tri = importlib.import_module(transport)
                logging.debug("imported {}".format(transport))
                tr = tri.Transport(self.que)
                logging.debug("created obj")
                if tr.is_init() is True:
                    if self.verbose:
                        logging.debug("Transport {} loaded.".format(tr.name()))
                    trans.append(tr)
                else:
                    if self.verbose:
                        logging.warning("Transport {} failed to initialize".format(
                            tr.get_name()))
            except:
                logging.warning("Internal error, import of {} failed, transport not available.".format(
                    transport))

        if len(trans) == 0:
            logging.error(
                "No transport available, cannot connect.")
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


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    brd = MillenniumChess(rescan=True, verbose=True)
