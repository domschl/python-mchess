''' Web interface using aiohttp '''
import logging
import json
import threading
import asyncio
import ssl
import aiohttp
from aiohttp import web
import chess
import chess.pgn
import time
import os


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
            if isinstance(self.prefs['bind_address'], list) is True:
                self.bind_addresses = self.prefs['bind_address']
            else:
                self.bind_addresses = self.prefs['bind_address']                
        else:
            self.bind_addresses = 'localhost'
            self.log.warning(
                f'Bind_address not configured, defaulting to {self.bind_address}, set to "[\'0.0.0.0\']" for remote accessibility'
            )

        self.private_key = None
        self.public_key = None
        self.tls = False
        if 'tls' in self.prefs and self.prefs['tls'] is True:
            if 'private_key' not in self.prefs or 'public_key' not in self.prefs:
                self.log.error("Cannot configure tls without public_key and private_key configured!")
                self.log.warning("Downgraded to tls=False")
            else:
                if os.path.exists(self.prefs['private_key']) is False:
                    self.log.error(f"Private key file {self.prefs['private_key']} does not exist, downgrading to no TLS")
                elif os.path.exists(self.prefs['public_key']) is False:
                    self.log.error(f"Public key file {self.prefs['public_key']} does not exist, downgrading to no TLS")
                else:
                    self.private_key = self.prefs['private_key']
                    self.public_key = self.prefs['public_key']
                    self.tls = True

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
        self.worker = threading.Thread(target=self.web_agent_thread, args=())
        self.worker.setDaemon(True)
        self.worker.start()
        self.active = True

    def web_agent_thread(self):
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
        if self.tls is True:
            self.ssl_context = ssl.SSLContext()  # = TLS
            try:
                self.ssl_context.load_cert_chain(self.public_key, self.private_key)
            except Exception as e:
                self.log.error(f"Cannot create cert chain: {e}, not using TLS")
                self.tls = False
        asyncio.run(self.async_web_agent())
        while self.active is True:
            time.sleep(0.1)
        self.log.info("Web starter thread stopped")

    async def async_web_agent(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        self.log.info("Starting web runner")
        if self.tls is True:
            self.log.info(f"TLS active, bind={self.bind_addresses}, port={self.port}")
            print(f"Webclient at: https://localhost:{self.port}")
            site = web.TCPSite(runner, self.bind_addresses, self.port, ssl_context=self.ssl_context)
        else:
            self.log.info(f"TLS NOT active, bind={self.bind_addresses}, port={self.port}")
            site = web.TCPSite(runner, self.bind_addresses, self.port)            
            print(f"Webclient at: http://localhost:{self.port}")
        await site.start()
        self.log.info("Web server active")
        while self.active:
            await asyncio.sleep(0.1)
        self.log.info("Web server stopped")
        
    def web_root(self, request):
        return web.FileResponse('web/index.html')

    def web_favicon(self, request):
        return web.FileResponse('web/favicon.ico')

    def mchess_script(self, request):
        return web.FileResponse('web/scripts/mchess.js')

    def mchess_style(self, request):
        return web.FileResponse('web/styles/mchess.css')

    async def send_out(self, ws, text):
        await ws.send_str(text)

    def send2ws(self, ws, text):
        if ws.closed:
            self.log.warning(f"Closed websocket encountered: {ws}")
            return False
        self.log.info(f"Sending {text} to {ws}")
        asyncio.run(self.send_out(ws, text))
        return True

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        thread_log = logging.getLogger("ThrdWeb")
        thread_log.setLevel(logging.INFO)

        await ws.prepare(request)

        if ws not in self.ws_clients:
            self.ws_clients.append(ws)
            thread_log.info(f"New ws client {ws}! (clients: {len(self.ws_clients)})")
        else:
            thread_log.info(f"Client already registered! (clients: {len(self.ws_clients)})")

        if self.last_board is not None and self.last_attribs is not None:
            msg = {'cmd': 'display_board', 'fen': self.last_board.fen(), 'pgn': self.last_pgn,
                   'attribs': self.last_attribs}
            try:
                await ws.send_str(json.dumps(msg))
            except Exception as e:
                thread_log.warning(
                    "Sending to WebSocket client {} failed with {}".format(ws, e))
                return
        for actor in self.agent_state_cache:
            msg = self.agent_state_cache[actor]
            try:
                await ws.send_str(json.dumps(msg))
            except Exception as e:
                thread_log.warning(
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
                # if msg.data is not None:
                thread_log.info(
                    "Client ws_dispatch: ws:{} msg:{}".format(ws, msg.data))
                try:
                    self.log.info(f"Received: {msg.data}")
                    self.appque.put(json.loads(msg.data))
                except Exception as e:
                    thread_log.warning(f"WebClient sent invalid JSON: {msg.data}: {e}")
                # if msg.data == 'close':
                #     await ws.close()
                # else:
                #     await ws.send_str(msg.data + '/answer')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                thread_log.warning(f'ws connection closed with exception {ws.exception()}')
                break
            else:
                thread_log.error(f"Unexpected message {msg.data}, of type {msg.type}")
                break
        thread_log.warning(f"WS-CLOSE: {ws}")
        self.ws_clients.remove(ws)

        return ws

    def agent_ready(self):
        return self.active

    def quit(self):
        self.socket_thread_active = False

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        self.last_board = board
        self.last_attribs = attribs
        self.log.info(f"Display board, clients: {len(self.ws_clients)}")
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
        self.log.info(f"web set valid called, clients: {len(self.ws_clients)}.")
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
