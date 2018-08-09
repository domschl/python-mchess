import logging

import mill_prot
try:
    from bluepy.btle import Scanner, DefaultDelegate, Peripheral
    bluepy_ble_support = True
except:
    bluepy_ble_support = False


class Transport():
    def __init__(self, que):
        if bluepy_ble_support == False:
            self.init = False
            return
        self.log = logging.getLogger("MilleniumPyBlueBt")
        self.que = que  # asyncio.Queue()
        self.init = True
        self.is_open = False
        self.log.debug("init ok")

    def search_board(self):
        self.log.debug("searching for boards")

        return None

    def test_board(self, address):
        return None

    def open_mt(self, address):
        self.log.debug("open_mt {}".format(address))
        return False

    def write_mt(self, msg):
        return False

    def get_name(self):
        return "millcon_pyblue_bt"

    def is_init(self):
        return self.init
