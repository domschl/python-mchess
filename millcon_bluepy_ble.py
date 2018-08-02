import logging

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
        self.que = que  # asyncio.Queue()

        logging.error("BLE not implemented")
        self.init = False

    def get_name(self):
        return "millcon_bluepy_ble"

    def is_init(self):
        return self.init
