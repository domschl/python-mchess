import logging
import time
import threading
import queue
import json
import copy
import socket

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
        self.last_board = None

        self.port = 8001

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
        self.app.add_url_rule('/images/turquoise.png',
                              'logo', self.mchess_logo)
        self.active = True

        self.sockets.add_url_rule('/ws', 'ws', self.ws_sockets)
        self.ws_clients = {}
        self.ws_handle = 0

        self.socket_handler()  # Start threads for web and ws:sockets

    def node_modules(self, path):
        # print("NODESTUFF")
        return send_from_directory('web/node_modules', path)

    def web_root(self):
        return self.app.send_static_file('index.html')

    def web_favicon(self):
        return self.app.send_static_file('favicon.ico')

    def ws_dispatch(self, ws, message):
        print("Client: ws:{} msg:{}".format(ws, message))

    def ws_sockets(self, ws):
        self.ws_handle += 1
        handle = self.ws_handle
        if self.last_board is not None:
            msg = {'fen': self.last_board.fen()}
            ws.send(json.dumps(msg))
        while not ws.closed:
            self.ws_clients[handle] = ws
            message = ws.receive()
            self.ws_dispatch(handle, message)
        del self.ws_clients[handle]

    def mchess_script(self):
        return self.app.send_static_file('scripts/mchess.js')

    def mchess_style(self):
        return self.app.send_static_file('styles/mchess.css')

    def mchess_logo(self):
        return self.app.send_static_file('images/turquoise.png')

    def sock_connect(self):
        print("CONNECT")

    def sock_message(self, message):
        print("RECEIVED: {}".format(message))

    def agent_ready(self):
        return self.active

    def quit(self):
        self.socket_thread_active = False

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        self.last_board = board
        msg = {'fen': board.fen()}
        for w in self.ws_clients:
            self.ws_clients[w].send(json.dumps(msg))

    def display_move(self, move_msg):
        pass

    def display_info(self, board, info):
        ninfo = copy.deepcopy(info)
        nboard = copy.deepcopy(board)
        is_first = True
        if 'variant' in ninfo:
            ml = '<div class="variant">'
            for move in ninfo['variant']:
                if is_first is False:
                    if nboard.turn is True:
                        ml += '&nbsp '
                    else:
                        ml += '&nbsp'
                else:
                    is_first = False
                if nboard.turn is True:
                    ml += '<span class="movenr">{}.</span>&nbsp'.format(
                        nboard.fullmove_number)
                ml += nboard.san(move)
                nboard.push(move)
            ml += '</div>'
            ninfo['variant'] = ml

        msg = {'fenref': nboard.fen(), 'info': ninfo}
        for w in self.ws_clients:
            self.ws_clients[w].send(json.dumps(msg))

    def set_valid_moves(self, board, vals):
        self.socket_moves = []
        if vals != None:
            for v in vals:
                self.socket_moves.append(vals[v])

    def socket_event_worker_thread(self, appque, log, app, WebSocketHandler):
        server = pywsgi.WSGIServer(
            ('0.0.0.0', self.port), app, handler_class=WebSocketHandler)
        print("Web browser: http://{}:{}".format(socket.gethostname(), self.port))
        server.serve_forever()

    def socket_handler(self):
        self.socket_thread_active = True

        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.appque, self.log, self.app, WebSocketHandler))
        self.socket_event_thread.setDaemon(True)
        self.socket_event_thread.start()
