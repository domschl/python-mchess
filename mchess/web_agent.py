import logging
import time
import threading
import queue
import json
import copy
import socket
import mimetypes
import chess
import chess.pgn

from flask import Flask, send_from_directory
from flask_sockets import Sockets

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler


mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/javascript', '.js')


class WebAgent:
    def __init__(self, appque, prefs):
        self.name = 'WebAgent'
        self.prefs = prefs
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
        self.last_attribs = None
        self.last_pgn = None

        self.port = 8001

        self.socket_moves = []
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        disable_web_logs = True
        if disable_web_logs is True:
            wlog = logging.getLogger('werkzeug')
            wlog.setLevel(logging.ERROR)
            slog = logging.getLogger('geventwebsocket.handler')
            slog.setLevel(logging.ERROR)
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
        self.log.debug("Client ws_dispatch: ws:{} msg:{}".format(ws, message))
        try:
            self.appque.put(json.loads(message))
        except Exception as e:
            self.log.debug("WebClient sent invalid JSON: {}".format(e))

    def ws_sockets(self, ws):
        self.ws_handle += 1
        handle = self.ws_handle
        if self.last_board is not None and self.last_attribs is not None:
            msg = {'fen': self.last_board.fen(), 'pgn': self.last_pgn,
                   'attribs': self.last_attribs}
            try:
                ws.send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(w, e))
                return
        self.ws_clients[handle] = ws
        while not ws.closed:
            message = ws.receive()
            self.ws_dispatch(handle, message)
        del self.ws_clients[handle]

    def mchess_script(self):
        return self.app.send_static_file('scripts/mchess.js')

    def mchess_style(self):
        return self.app.send_static_file('styles/mchess.css')

    def mchess_logo(self):
        return self.app.send_static_file('images/turquoise.png')

#    def sock_connect(self):
#        print("CONNECT")

#    def sock_message(self, message):
#        print("RECEIVED: {}".format(message))

    def agent_ready(self):
        return self.active

    def quit(self):
        self.socket_thread_active = False

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        self.last_board = board
        self.last_attribs = attribs
        try:
            game = chess.pgn.Game().from_board(board)
            game.headers["White"] = attribs["white_name"]
            game.headers["Black"] = attribs["black_name"]
            pgntxt = str(game)
        except Exception as e:
            self.log.error("Invalid PGN position, {}".format(e))
            return
        self.last_pgn = pgntxt
        # print("pgn: {}".format(pgntxt))
        msg = {'fen': board.fen(), 'pgn': pgntxt, 'attribs': attribs}
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(w, e))

    def display_move(self, move_msg):
        pass

    def display_info(self, board, info):
        ninfo = copy.deepcopy(info)
        nboard = copy.deepcopy(board)
        if 'variant' in ninfo:
            ml = []
            if nboard.turn is False:
                mv = (nboard.fullmove_number,)
                mv += ("..",)
            for move in ninfo['variant']:
                if move is None:
                    self.log.error("None-move in variant: {}".format(ninfo))
                if nboard.turn is True:
                    mv = (nboard.fullmove_number,)
                try:
                    san = nboard.san(move)
                except Exception as e:
                    self.log.warning(
                        "Internal error '{}' at san conversion.".format(e))
                    san = None
                if san is not None:
                    mv += (san,)
                else:
                    self.log.info(
                        "Variant cut off due to san-conversion-error: '{}'".format(mv))
                    break
                if nboard.turn is False:
                    ml.append(mv)
                    mv = ""
                nboard.push(move)
            if mv != "":
                ml.append(mv)
                mv = ""
            ninfo['variant'] = ml

        msg = {'fenref': nboard.fen(), 'info': ninfo}
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(w, e))

    def agent_states(self, msg):
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(w, e))

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
