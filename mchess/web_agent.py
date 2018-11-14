import logging
import time
import threading
import queue

import chess
from flask import Flask, send_from_directory
from flask_sockets import Sockets

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler


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

        # wlog = logging.getLogger('werkzeug')
        # wlog.setLevel(logging.ERROR)
        self.app = Flask(__name__, static_folder='web')
        # self.app.config['ENV'] = "MChess_Agent"
        self.app.config['SECRET_KEY'] = 'somesecret'  # TODO: Investigate
        self.app.debug = False
        self.app.use_reloader = False

        self.sockets = Sockets(self.app)

        self.app.add_url_rule('/node_modules/<path:path>',
                              'node_modules', self.node_modules)
        self.app.add_url_rule('/', 'root', self.web_root)
        self.app.add_url_rule('/favicon.ico', 'favicon', self.web_favicon)
        self.app.add_url_rule('/index.html', 'index', self.web_root)
        self.app.add_url_rule('/scripts/mchess.js',
                              'script', self.mchess_script)
        self.app.add_url_rule('/styles/mchess.css',
                              'style', self.mchess_style)
        self.active = True

        self.sockets.add_url_rule('/ws', 'ws', self.ws_sockets)

        self.socket_handler()  # Start threads for web and ws:sockets

    def node_modules(self, path):
        # print("NODESTUFF")
        return send_from_directory('web/node_modules', path)

    def web_root(self):
        return self.app.send_static_file('index.html')

    def web_favicon(self):
        return self.app.send_static_file('favicon.ico')

    def ws_sockets(self, ws):
        while not ws.closed:
            message = ws.receive()
            ws.send(message)

    def mchess_script(self):
        return self.app.send_static_file('scripts/mchess.js')

    def mchess_style(self):
        return self.app.send_static_file('styles/mchess.css')

    def sock_connect(self):
        print("CONNECT")

    def sock_message(self, message):
        print("RECEIVED: {}".format(message))

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

    def socket_event_worker_thread(self, appque, log, app, WebSocketHandler):
        server = pywsgi.WSGIServer(
            ('0.0.0.0', 8001), app, handler_class=WebSocketHandler)
        server.serve_forever()

    def socket_handler(self):
        self.socket_thread_active = True

        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.appque, self.log, self.app, WebSocketHandler))
        self.socket_event_thread.setDaemon(True)
        self.socket_event_thread.start()
