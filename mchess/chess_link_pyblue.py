''' implementation framework for additional bluetooth module, not functional '''
import logging

# import chess_link_protocol as clp

# TODO: expand empty framework with actual functionality!


class Transport():
    ''' non-functional frame '''
    def __init__(self, que):
        self.log = logging.getLogger("ChessLinkPyBlue")
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
        self.log.debug(f"open_mt {address}")
        return False

    def write_mt(self, msg):
        return False

    def get_name(self):
        return "chess_link_pyblue"

    def is_init(self):
        return self.init
