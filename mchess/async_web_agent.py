''' Web interface using aiohttp '''
import logging
# import time
# import queue
import json
# import os
import threading
import asyncio
# import copy
import aiohttp
from aiohttp import web
import chess
import chess.pgn


class AsyncWebAgent:
    def __init__(self, appque, prefs):
        self.name = 'AsyncWebAgent'
        self.prefs = prefs
        self.log = logging.getLogger("AsyncWebAgent")
        self.log.setLevel(logging.INFO)
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
        self.socket_thread_active = False
        self.ws_clients = []

        if 'port' in self.prefs:
            self.port = self.prefs['port']
        else:
            self.port = 8001
            self.log.warning(f'Port not configured, defaulting to {self.port}')

        if 'bind_address' in self.prefs:
            self.bind_address = self.prefs['bind_address']
        else:
            self.bind_address = 'localhost'
            self.log.warning(
                f'Bind_address not configured, defaulting to f{self.bind_address}, set to "0.0.0.0" for remote accessibility')

        self.private_key = None
        self.public_key = None
        if 'tls' in self.prefs and self.prefs['tls'] is True:
            if 'private_key' not in self.prefs or 'public_key' not in self.prefs:
                self.log.error(
                    "Cannot configure tls without public_key and private_key configured!")
            else:
                self.private_key = prefs['private_key']
                self.public_key = prefs['public_key']

        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE),
                                 (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK),
                                 (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.worker = threading.Thread(target=self.async_web_agent_thread, args=())
        self.worker.setDaemon(True)
        self.worker.start()
        self.active = True

    def async_web_agent_thread(self):
        self.socket_thread_active = True
        asyncio.set_event_loop(self.event_loop)
        self.app = web.Application(debug=True)
        self.app.add_routes([web.static('/node_modules', 'web/node_modules'),
                             web.static('/images', 'web/images')])

        self.app.add_routes([web.get('/', self.web_root),
                             web.get('/favicon.ico', self.web_favicon),
                             web.get('/scripts/mchess.js', self.mchess_script),
                             web.get('/styles/mchess.css', self.mchess_style)])
        self.app.add_routes([web.get('/ws', self.websocket_handler)])
        web.run_app(self.app, handle_signals=False)  # in threads: no signals!
        while self.socket_thread_active:
            asyncio.sleep(0.1)

        # self.sockets.add_url_rule('/ws', 'ws', self.ws_sockets)
        # self.ws_clients = {}
        # self.ws_handle = 0
        # self.log.debug("Initializing web server...")
        # self.socket_handler()  # Start threads for web and ws:sockets

    def web_root(self, request):
        return web.FileResponse('web/index.html')

    def web_favicon(self, request):
        return web.FileResponse('web/favicon.ico')

    def mchess_script(self, request):
        return web.FileResponse('web/scripts/mchess.js')

    def mchess_style(self, request):
        return web.FileResponse('web/styles/mchess.css')

    def send2ws(self, ws, text):
        if ws.closed:
            self.log.warning(f"Closed websocket encountered: {ws}")
            return False
        asyncio.run_coroutine_threadsafe(ws.send_str(text), self.event_loop)
        return True

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse(autoclose=False)
        await ws.prepare(request)

        if ws not in self.ws_clients:
            self.ws_clients.append(ws)

        if self.last_board is not None and self.last_attribs is not None:
            msg = {'cmd': 'display_board', 'fen': self.last_board.fen(), 'pgn': self.last_pgn,
                   'attribs': self.last_attribs}
            try:
                await ws.send_str(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    "Sending to WebSocket client {} failed with {}".format(ws, e))
                return
        for actor in self.agent_state_cache:
            msg = self.agent_state_cache[actor]
            try:
                await ws.send_str(json.dumps(msg))
            except Exception as e:
                self.log.warning(
                    f"Failed to update agents states to new web-socket client: {e}")
        if self.uci_engines_cache != {}:
            await ws.send_str(json.dumps(self.uci_engines_cache))
        if self.display_move_cache != {}:
            await ws.send_str(json.dumps(self.display_move_cache))
        if self.valid_moves_cache != {}:
            await ws.send_str(json.dumps(self.valid_moves_cache))
        if self.game_stats_cache != {}:
            await ws.send_str(json.dumps(self.game_stats_cache))

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data is not None:
                    self.log.info(
                        "Client ws_dispatch: ws:{} msg:{}".format(ws, msg.data))
                    try:
                        self.log.info(f"Received: {msg.data}")
                        self.appque.put(json.loads(msg.data))
                    except Exception as e:
                        self.log.warning(f"WebClient sent invalid JSON: {msg.data}: {e}")
                # if msg.data == 'close':
                #     await ws.close()
                # else:
                #     await ws.send_str(msg.data + '/answer')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.log.warning(f'ws connection closed with exception {ws.exception()}')
            else:
                self.log.error(f"Unexpected message {msg.data}, of type {msg.type}")
            
        self.log.warning(f"WS-CLOSE: {ws}")
        self.ws_clients.remove(ws)

        return ws

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
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(msg)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending board to WebSocket client {} failed with {}".format(ws, e))

    def display_move(self, move_msg):
        self.log.info(f"AWS display move to {len(self.ws_clients)} clients")
        self.display_move_cache = move_msg
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(move_msg)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    f"Sending display_move {move_msg} to WebSocket client {ws} failed with {e}")

    def set_valid_moves(self, board, vals):
        self.log.info("web set valid called.")
        self.valid_moves_cache = {
            "cmd": "valid_moves",
            "valid_moves": [],
            'actor': 'AsyncWebAgent'
        }
        if vals is not None:
            for v in vals:
                self.valid_moves_cache['valid_moves'].append(vals[v])
        self.log.info(f"Valid-moves: {self.valid_moves_cache}")
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(self.valid_moves_cache)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending valid_moves to WebSocket client {} failed with {}".format(ws, e))

    def display_info(self, board, info):
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(info)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending display-info to WebSocket client {} failed with {}".format(ws, e))

    def engine_list(self, msg):
        for engine in msg["engines"]:
            self.log.info(f"Engine {engine} announced.")
        self.uci_engines_cache = msg
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(msg)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending uci-info to WebSocket client {} failed with {}".format(ws, e))

    def game_stats(self, stats):
        msg = {'cmd': 'game_stats', 'stats': stats, 'actor': 'AsyncWebAgent'}
        self.game_stats_cache = msg
        self.log.info(f"Game stats: {msg}")
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(msg)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending game_stats to WebSocket client {} failed with {}".format(ws, e))

    def agent_states(self, msg):
        self.agent_state_cache[msg['actor']] = msg
        for ws in self.ws_clients:
            try:
                if self.send2ws(ws, json.dumps(msg)) is False:
                    self.ws_clients.remove(ws)
            except Exception as e:
                self.log.warning(
                    "Sending agent-state info to WebSocket client {} failed with {}".format(ws, e))
