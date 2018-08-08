import time
import logging
import os
import platform
import sys
import struct
import threading
import asyncio
import queue
import json
import importlib
import copy

try:
    import chess
    import chess.uci
    chess_support = True
except:
    chess_support = False


class MillenniumChess:
    def __init__(self, appque):
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.transports = {'Darwin': ['millcon_usb', 'millcon_bluepy_ble'], 'Linux': [
            'millcon_bluepy_ble', 'millcon_usb'], 'Windows': ['millcon_usb']}

        self.log = logging.getLogger('Millenium')
        self.log.info("Millenium starting")
        if sys.version_info[0] < 3:
            self.log.critical("FATAL: You need Python 3.x to run this module.")
            exit(-1)

        if platform.system() not in self.transports:
            self.log.critical(
                "Fatal: {} is not a supported platform.".format(platform.system()))
            msg = "Supported are: "
            for p in self.transports:
                msg += '{} '.format(p)
            self.log.info(msg)
            exit(-1)

        self.appque = appque
        self.trans = None
        self.trque = queue.Queue()  # asyncio.Queue()
        self.mill_config = None
        self.connected = False
        self.position = None
        self.reference_position = None
        self.board_inverted = False
        self.legal_moves = None
        found_board = False

        self.thread_active = True
        self.event_thread = threading.Thread(
            target=self.event_worker_thread, args=(self.trque,))
        self.event_thread.setDaemon(True)
        self.event_thread.start()

        try:
            with open("millennium_config.json", "r") as f:
                self.mill_config = json.load(f)
                self.log.debug('Checking default configuration for board via {} at {}'.format(
                    self.mill_config['transport'], self.mill_config['address']))
                trans = self._open_transport(self.mill_config['transport'])
                if trans is not None:
                    if trans.test_board(self.mill_config['address']) is not None:
                        self.log.debug('Default board operational.')
                        found_board = True
                        self.trans = trans
                    else:
                        self.log.warning(
                            'Default board not available, start scan.')
                        self.mill_config = None
        except Exception as e:
            self.mill_config = None
            self.log.debug(
                'No valid default configuration, starting board-scan: {}'.format(e))

        if found_board is False:
            address = None
            for transport in self.transports[platform.system()]:
                try:
                    tri = importlib.import_module(transport)
                    self.log.debug("imported {}".format(transport))
                    tr = tri.Transport(self.trque)
                    self.log.debug("created obj")
                    if tr.is_init() is True:
                        self.log.debug(
                            "Transport {} loaded.".format(tr.get_name()))
                        address = tr.search_board()
                        if address is not None:
                            self.log.info("Found board on transport {} at address {}".format(
                                tr.get_name(), address))
                            self.mill_config = {
                                'transport': tr.get_name(), 'address': address}
                            self.trans = tr
                            try:
                                with open("millennium_config.json", "w") as f:
                                    json.dump(self.mill_config, f)
                            except Exception as e:
                                self.log.error("Failed to save default configuration {} to {}: {}".format(
                                    self.mill_config, "millennium_config.json", e))
                            break
                    else:
                        self.log.warning("Transport {} failed to initialize".format(
                            tr.get_name()))
                except Exception as e:
                    self.log.warning("Internal error, import of {} failed: {}".format(
                        transport, e))

        if self.mill_config is None or self.trans is None:
            self.log.error(
                "No transport available, cannot connect.")
            return
        else:
            self.log.info('Valid board available on {} at {}'.format(
                self.mill_config['transport'], self.mill_config['address']))
            if platform.system() != 'Windows':
                if os.geteuid() == 0:
                    self.log.warning(
                        'Do not run as root, once intial BLE scan is done.')
            self.connected = self.trans.open_mt(self.mill_config['address'])

    def event_worker_thread(self, que):
        self.log.debug('Millenium worker thread started.')
        while self.thread_active:
            if self.trque.empty() is False:
                msg = self.trque.get()
                if len(msg) > 0:
                    if msg[0] == 's':
                        if len(msg) == 67:
                            rp = msg[1:65]
                            val_pos = True
                            position = [
                                [0 for x in range(8)] for y in range(8)]
                            if len(rp) == 64:
                                for y in range(8):
                                    for x in range(8):
                                        c = rp[7-x+y*8]
                                        i = self.figrep['ascii'].find(c)
                                        if i == -1:
                                            self.log.warning(
                                                "Invalid char in raw position: {}".format(c))
                                            val_pos = False
                                            continue
                                        else:
                                            f = self.figrep['int'][i]
                                            if self.board_inverted == False:
                                                position[y][x] = f
                                            else:
                                                position[7-y][7-x] = f
                            else:
                                val_pos = False
                                self.log.warning(
                                    "Error in board position, received {}".format(len(rp)))
                                continue
                        else:
                            val_pos = False
                            self.log.error(
                                'Incomplete board position, {}'.format(msg))
                        if val_pos is True:
                            fen = self.position_to_fen(position)
                            sfen = self.short_fen(fen)
                            if sfen == "RNBKQBNR/PPPPPPPP/8/8/8/8/pppppppp/rnbkqbnr":
                                if self.board_inverted == False:
                                    self.log.info("Cable-left board detected.")
                                    self.board_inverted = True
                                    position_inv = copy.deepcopy(position)
                                    for x in range(8):
                                        for y in range(8):
                                            position[x][y] = position_inv[7-x][7-y]
                                else:
                                    self.log.info(
                                        "Cable-right board detected.")
                                    self.board_inverted = False
                                    position_inv = copy.deepcopy(position)
                                    for x in range(8):
                                        for y in range(8):
                                            position[x][y] = position_inv[7-x][7-y]
                            fen = self.position_to_fen(position)
                            sfen = self.short_fen(fen)

                            if sfen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                                cmd = {'new game': '', 'actor': 'eboard'}
                                self.new_game(position)
                                self.appque.put(cmd)

                            self.position = position
                            if self.reference_position == None:
                                self.reference_position = position
                            self.show_delta(
                                self.reference_position, self.position)
                            # self.print_position_ascii(position)
                            self.appque.put({'fen': fen})
                            self.check_move(position)
                    if msg[0] == 'v':
                        self.log.debug('got version reply')
                        if len(msg) == 7:
                            version = '{}.{}'.format(
                                msg[1]+msg[2], msg[3]+msg[4])
                            self.appque.put({'version': version})
                        else:
                            self.log.warning(
                                "Bad length of version-reply: {}".format(len(version)))

                    if msg[0] == 'l':
                        self.log.debug('got led-set reply')
                    if msg[0] == 'x':
                        self.log.debug('got led-off reply')
            else:
                time.sleep(0.1)

    def new_game(self, pos):
        self.reference_position = pos
        self.set_led_off()
        self.legal_moves = None

    def check_move(self, pos):
        fen = self.short_fen(self.position_to_fen(pos))
        if self.legal_moves is not None and fen in self.legal_moves:
            self.appque.put(
                {'move': {'uci': self.legal_moves[fen], 'fen': fen, 'actor': 'eboard'}})
            self.reference_position = pos
            self.set_led_off()
        return True

    def move_from(self, fen, legal_moves):
        self.legal_moves = legal_moves
        self.reference_position = self.fen_to_position(fen)
        self.show_delta(self.reference_position, self.position)

    def show_delta(self, pos1, pos2):
        dpos = [[0 for x in range(8)] for y in range(8)]
        for y in range(8):
            for x in range(8):
                if pos2[y][x] != pos1[y][x]:
                    if pos1[y][x] != 0:
                        dpos[y][x] = 1
                    else:
                        dpos[y][x] = 2
        self.set_led(dpos)

    def set_led(self, pos):
        if self.connected is True:
            leds = [[0 for x in range(9)] for y in range(9)]
            cmd = "L20"
            for y in range(8):
                for x in range(8):
                    if pos[y][x] != 0:
                        if self.board_inverted == False:
                            leds[7-x][y] = pos[y][x]
                            leds[7-x+1][y] = pos[y][x]
                            leds[7-x][y+1] = pos[y][x]
                            leds[7-x+1][y+1] = pos[y][x]
                        else:
                            leds[x][7-y] = pos[y][x]
                            leds[x+1][7-y] = pos[y][x]
                            leds[x][7-y+1] = pos[y][x]
                            leds[x+1][7-y+1] = pos[y][x]

            for y in range(9):
                for x in range(9):
                    if leds[y][x] == 0:
                        cmd = cmd + "00"
                    elif leds[y][x] == 1:
                        cmd = cmd + "0F"
                    else:
                        cmd = cmd + "F0"

            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    def set_led_off(self):
        if self.connected is True:
            self.trans.write_mt("X")
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    def short_fen(self, fen):
        i = fen.find(' ')
        if i == -1:
            self.log.error(
                'Invalid fen position <{}> in short_fen'.format(fen))
            return None
        else:
            return fen[:i]

    def position_to_fen(self, position):
        fen = ""
        blanks = 0
        for y in range(8):
            for x in range(8):
                f = position[7-y][x]
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        c = self.figrep['ascii'][i]
                        break
                if c == '?':
                    self.log.error(
                        "Internal FEN error, could not translation {} at {}{}".format(c, y, x))
                    return ""
                if c == '.':
                    blanks = blanks + 1
                else:
                    if blanks > 0:
                        fen += str(blanks)
                        blanks = 0
                    fen += c
            if blanks > 0:
                fen += str(blanks)
                blanks = 0
            if y < 7:
                fen += '/'
        fen += ' w KQkq - 0 1'
        return fen

    def fen_to_position(self, fen):
        position = [[0 for x in range(8)] for y in range(8)]
        fenp = self.short_fen(fen)
        fi = 0
        for y in range(8):
            x = 0
            while x < 8:
                c = fenp[fi]
                fi += 1
                if c >= '1' and c <= '8':
                    x += int(c)
                    continue
                ci = -99
                for i in range(len(self.figrep['ascii'])):
                    if self.figrep['ascii'][i] == c:
                        ci = self.figrep['int'][i]
                        break
                if ci == -99:
                    self.log.error(
                        "Internal FEN2 error decoding {} at {}{}".format(c, y, x))
                    return []
                position[7-y][x] = ci
                x += 1
            if y < 7 and fenp[fi] != '/':
                self.log.error(
                    "Illegal fen: missing '/' {}{}: {}[{}]".format(y, x, fenp[fi], fi))
                return []
            fi += 1
        return position

    def print_position_ascii(self, position):
        print("  +------------------------+")
        for y in range(8):
            print("{} |".format(8-y), end="")
            for x in range(8):
                f = position[7-y][x]
                if (x+y) % 2 == 0:
                    f = f*-1
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        c = self.figrep['unic'][i]
                        break
                if (x+y) % 2 == 0:
                    print("\033[7m {} \033[m".format(c), end="")
                else:
                    print(" {} ".format(c), end='')
            print("|")
        print("  +------------------------+")
        print("    A  B  C  D  E  F  G  H")

    def _open_transport(self, transport):
        try:
            tri = importlib.import_module(transport)
            self.log.debug("imported {}".format(transport))
            tr = tri.Transport(self.trque)
            self.log.debug("created obj")
            if tr.is_init() is True:
                self.log.debug("Transport {} loaded.".format(tr.get_name()))
                return tr
            else:
                self.log.warning("Transport {} failed to initialize".format(
                    tr.get_name()))
        except:
            self.log.warning("Internal error, import of {} failed, transport not available.".format(
                transport))
        return None

    def get_version(self):
        if self.connected is True:
            self.trans.write_mt("V")
        else:
            self.log.warning(
                "Not connected to Millennium board, can't get version.")
        return '?'

    def get_position(self):
        if self.connected is True:
            self.trans.write_mt("S")
        else:
            self.log.warning(
                "Not connected to Millennium board, can't get position.")
        return '?'

    def set_board_orientation(self, cable_right):
        if cable_right is True:
            self.board_inverted = False
        else:
            self.board_inverted = True

    def get_board_orientation(self):
        return self.board_inverted


class ChessBoardHelper:
    def __init__(self, appque):
        self.appque = appque
        self.log = logging.getLogger('ChessBoardHelper')
        self.kbd_moves = []

    def valid_moves(self, cbrd):
        vals = {}
        for mv in cbrd.legal_moves:
            cbrd.push(mv)
            vals[brd.short_fen(cbrd.fen())] = mv.uci()
            cbrd.pop()
        logging.debug("valid moves: {}".format(vals))
        return vals

    def load_engines(self):
        with open('uci_engines.json', 'r') as f:
            self.engines = json.load(f)['engines']
            logging.debug(self.engines)
            return self.engines

    class UciHandler(chess.uci.InfoHandler):
        def __init__(self):
            self.que = None
            self.last_pv_move = ""
            self.log = logging.getLogger('UciHandler')
            super().__init__()

        def post_info(self):
            # Called whenever a complete info line has been processed.
            # print(self.info)
            super().post_info()  # Release the lock

        def on_bestmove(self, bestmove, ponder):
            self.log.info("Best: {}".format(bestmove))
            self.que.put({'move': {
                'uci': bestmove.uci(),
                'actor': 'uci-engine'
            }})
            self.last_pv_move = ""
            super().on_bestmove(bestmove, ponder)

        def pv(self, move):
            if self.last_pv_move != move[0]:
                self.log.info("PV: {}".format(move[0]))
                self.last_pv_move = move[0]
            super().pv(move)

    def uci_handler(self, engine):
        self.info_handler = self.UciHandler()
        self.info_handler.que = self.appque
        engine.info_handlers.append(self.info_handler)

    def set_keyboard_valid(self, vals):
        self.kbd_moves = []
        if vals != None:
            for v in vals:
                self.kbd_moves.append(vals[v])

    def kdb_event_worker_thread(self, appque, log):
        while self.kdb_thread_active:
            cmd = input()
            log.info("keyboard: <{}>".format(cmd))
            if len(cmd) >= 1:
                if cmd in self.kbd_moves:
                    appque.put(
                        {'move': {'uci': cmd, 'actor': 'keyboard'}})
                elif cmd[0] == 'n':
                    log.info('requesting new game')
                    appque.put({'new game': '', 'actor': 'keyboard'})
                elif cmd[:4] == 'fen ':
                    appque.put('set position': {'fen': cmd[4:]})
                elif cmd == 'help':
                    log.info('n - new game')
                    log.info('e2e4 - valid move')
                else:
                    log.info(
                        'Unknown keyboard cmd <{}>, enter "help" for a list of valid commands.'.format(cmd))

    def keyboard_handler(self):
        self.kdb_thread_active = True
        self.kbd_event_thread = threading.Thread(
            target=self.kdb_event_worker_thread, args=(self.appque, self.log))
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()


if __name__ == '__main__':
    import chess
    import chess.uci

    if platform.system().lower() == 'windows':
        from ctypes import windll, c_int, byref
        stdout_handle = windll.kernel32.GetStdHandle(c_int(-11))
        mode = c_int(0)
        windll.kernel32.GetConsoleMode(c_int(stdout_handle), byref(mode))
        mode = c_int(mode.value | 4)
        windll.kernel32.SetConsoleMode(c_int(stdout_handle), mode)

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)
    appque = queue.Queue()
    brd = MillenniumChess(appque)
    bhlp = ChessBoardHelper(appque)
    bhlp.keyboard_handler()

    bhlp.load_engines()
    logging.info('{} engines loaded.'.format(len(bhlp.engines)))

    if len(bhlp.engines) > 0:
        engine = chess.uci.popen_engine(bhlp.engines[0]['path'])
        engine.uci()
        # options
        engine.isready()
        bhlp.uci_handler(engine)

    else:
        engine = None

    if brd.connected is True:
        brd.get_version()
        brd.get_position()
        while True:
            if appque.empty() is False:
                msg = appque.get()
                logging.debug("App received msg: {}".format(msg))
                if 'new game' in msg:
                    logging.info("New Game (by: {})".format(msg['actor']))
                    cbrd = chess.Board()
                    vals = bhlp.valid_moves(cbrd)
                    bhlp.set_keyboard_valid(vals)
                    brd.move_from(cbrd.fen(), vals)
                if 'move' in msg:
                    uci = msg['move']['uci']
                    logging.info("{} move: {}".format(
                        msg['move']['actor'], uci))
                    mv = chess.Move.from_uci(uci)
                    cbrd.push(mv)
                    if cbrd.is_check() and not cbrd.is_checkmate():
                        logging.info("Check!")
                    if cbrd.is_checkmate():
                        logging.info("Checkmate!")
                        if msg['move']['actor'] != 'eboard':
                            brd.move_from(cbrd.fen(), {})
                    else:
                        if msg['move']['actor'] == 'keyboard':
                            vals = bhlp.valid_moves(cbrd)
                            brd.move_from(cbrd.fen(), vals)
                            bhlp.set_keyboard_valid(None)
                            engine.position(cbrd)
                            engine.go(movetime=5000)
                        if msg['move']['actor'] == 'eboard':
                            bhlp.set_keyboard_valid(None)
                            engine.position(cbrd)
                            engine.go(movetime=5000)
                        if msg['move']['actor'] == 'uci-engine':
                            vals = bhlp.valid_moves(cbrd)
                            bhlp.set_keyboard_valid(vals)
                            brd.move_from(cbrd.fen(), vals)
            else:
                time.sleep(0.1)
            # brd.trans.mil.waitForNotifications(1.0)
