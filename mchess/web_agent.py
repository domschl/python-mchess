import logging
import threading
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
        self.agent_state_cache = {}
        self.uci_engines_cache = {}
        self.display_move_cache = {}
        self.valid_moves_cache = {}
        self.game_stats_cache = {}
        self.max_mpv = 1
        self.last_board = None
        self.last_attribs = None
        self.last_pgn = None

        if 'port' in self.prefs:
            self.port = self.prefs['port']
        else:
            self.port = 8001
            self.log.warning(f'Port not configured, defaulting to {self.port}')

        if 'bind_address' in self.prefs:
            self.bind_address = self.prefs['bind_address']
        else:
            self.bind_address = 'localhost'
            self.log.warning(f'Bind_address not configured, defaulting to f{self.bind_address}, set to "0.0.0.0" for remote accessibility')

        self.private_key = None
        self.public_key = None
        if 'tls' in self.prefs and self.prefs['tls'] is True:
            if 'private_key' not in self.prefs or 'public_key' not in self.prefs:
                self.log.error(f"Cannot configure tls without public_key and private_key configured!")
            else:
                self.private_key = prefs['private_key']
                self.public_key = prefs['public_key']

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
        self.app.config['SECRET_KEY'] = 'secretsauce'
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
        self.app.add_url_rule('/images/<path:path>',
                              'images', self.images)
        self.active = True

        self.sockets.add_url_rule('/ws', 'ws', self.ws_sockets)
        self.ws_clients = {}
        self.ws_handle = 0
        self.log.debug("Initializing web server...")
        self.socket_handler()  # Start threads for web and ws:sockets

    def node_modules(self, path):
        # print("NODESTUFF")
        return send_from_directory('web/node_modules', path)

    def web_root(self):
        return self.app.send_static_file('index.html')

    def web_favicon(self):
        return self.app.send_static_file('favicon.ico')

    def ws_dispatch(self, ws, message):
        # self.log.info(f"message received: {message}")
        if message is not None:
            self.log.debug("Client ws_dispatch: ws:{} msg:{}".format(ws, message))
            try:
                self.log.info(f"Received: {message}")
                self.appque.put(json.loads(message))
            except Exception as e:
                self.log.debug("WebClient sent invalid JSON: {}".format(e))

    def ws_sockets(self, ws):
        self.ws_handle += 1
        handle = self.ws_handle
        if self.last_board is not None and self.last_attribs is not None:
            msg = {'cmd': 'display_board', 'fen': self.last_board.fen(), 'pgn': self.last_pgn,
                   'attribs': self.last_attribs}
            try:
                ws.send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(handle, e))
                return
        for actor in self.agent_state_cache:
            msg = self.agent_state_cache[actor]
            try:
                ws.send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    f"Failed to update agents states to new web-socket client: {e}")
        if self.uci_engines_cache != {}:
            ws.send(json.dumps(self.uci_engines_cache))
        if self.display_move_cache != {}:
            ws.send(json.dumps(self.display_move_cache))
        if self.valid_moves_cache != {}:
            ws.send(json.dumps(self.valid_moves_cache))
        self.ws_clients[handle] = ws
        while not ws.closed:
            message = ws.receive()
            self.ws_dispatch(handle, message)
        del self.ws_clients[handle]

    def mchess_script(self):
        return self.app.send_static_file('scripts/mchess.js')

    def mchess_style(self):
        return self.app.send_static_file('styles/mchess.css')

    def images(self, path):
        return send_from_directory('web/images', path)

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
        msg = {'cmd': 'display_board', 'fen': board.fen(), 'pgn': pgntxt,
               'attribs': attribs}
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending board to WebSocket client {} failed with {}".format(w, e))

    def display_move(self, move_msg):
        self.display_move_cache = move_msg;
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(move_msg))
            except Exception as e:
                self.log.warning(
                    "Sending display_move to WebSocket client {} failed with {}".format(w, e))

    def set_valid_moves(self, board, vals):
        self.log.info("web set valid called.")
        self.valid_moves_cache = {
            "cmd": "valid_moves",
            "valid_moves": [],
            'actor': 'WebAgent'
        }
        if vals != None:
            for v in vals:
                self.valid_moves_cache['valid_moves'].append(vals[v])
        self.log.info(f"Valid-moves: {self.valid_moves_cache}")
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(self.valid_moves_cache))
            except Exception as e:
                self.log.warning(
                    "Sending display_move to WebSocket client {} failed with {}".format(w, e))

    def display_info(self, board, info):
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(info))
            except Exception as e:
                self.log.warning(
                    "Sending move-info to WebSocket client {} failed with {}".format(w, e))

    def engine_list(self, msg):
        for engine in msg["engines"]:
            self.log.info(f"Engine {engine} announced.")
        self.uci_engines_cache = msg
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending uci-info to WebSocket client {} failed with {}".format(w, e))

    def game_stats(self, stats):
        msg = {'cmd': 'game_stats', 'stats': stats, 'actor': 'WebAgent'}
        self.game_stats_cache = msg
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending game_stats to WebSocket client {} failed with {}".format(w, e))

    def agent_states(self, msg):
        self.agent_state_cache[msg['actor']] = msg
        for w in self.ws_clients:
            try:
                self.ws_clients[w].send(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending agent-state info to WebSocket client {} failed with {}".format(w, e))

    # def set_valid_moves(self, board, vals):
    #     self.socket_moves = []
    #     if vals != None:
    #         for v in vals:
    #             self.socket_moves.append(vals[v])

    def socket_event_worker_thread(self, appque, log, app, WebSocketHandler):
        if self.bind_address == '0.0.0.0':
            address = socket.gethostname()
        else:
            address = self.bind_address

        if self.private_key is None or self.public_key is None:
            server = pywsgi.WSGIServer(
                (self.bind_address, self.port), app, handler_class=WebSocketHandler)
            protocol='http'
            self.log.info(f"Web browser: {protocol}://{address}:{self.port}")
        else:
            server = pywsgi.WSGIServer(
                (self.bind_address, self.port), app, keyfile=self.private_key, certfile=self.public_key, handler_class=WebSocketHandler)
            protocol='https'
            self.log.info(f"Web browser: {protocol}://{address}:{self.port}")
        print(f"Web browser: {protocol}://{address}:{self.port}")
        server.serve_forever()

    def socket_handler(self):
        self.socket_thread_active = True

        self.socket_event_thread = threading.Thread(
            target=self.socket_event_worker_thread, args=(self.appque, self.log, self.app, WebSocketHandler))
        self.socket_event_thread.setDaemon(True)
        self.socket_event_thread.start()
