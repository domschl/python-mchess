import logging
import time
import threading
import queue

import chess
from flask import Flask


class WebAgent:
    def __init__(self, appque):
        self.name = 'WebAgent'
        self.log = logging.getLogger("WebAgent")
        self.appque = appque
        self.orientation = True
        self.active = False
        self.max_plies = 6

        self.display_cache = ""
        self.last_cursor_up = 0
        self.move_cache = ""
        self.info_cache = ""
        self.info_provider = {}
        self.max_mpv = 1

        self.socket_moves = []
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self.app = Flask(__name__)
        self.app.config['ENV'] = "MChess_Agent"
        self.app.debug = False
        self.app.use_reloader = False
        self.app.add_url_rule('/', 'root', self.hello_world)
        self.app.add_url_rule('/borg', 'borg', self.hello_borg)
        self.active = True

        self.socket_handler()

    def hello_world(self):
        return 'Hello, World!'

    def hello_borg(self):
        return 'The BORG!'

    def agent_ready(self):
        return self.active

    def quit(self):
        self.socket_thread_active = False

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        pass

    def display_move(self, move_msg):
        pass

    def display_info(self, board, info):
        pass

    def set_valid_moves(self, board, vals):
        self.socket_moves = []
        if vals != None:
            for v in vals:
                self.socket_moves.append(vals[v])

    def socket_event_worker_thread(self, appque, log, app):
        app.run()
        while self.socket_thread_active:
            time.sleep(0.1)

    def socket_handler(self):
        self.socket_thread_active = True
        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.appque, self.log, self.app))
        self.socket_event_thread.setDaemon(True)
        self.socket_event_thread.start()
