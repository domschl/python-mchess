import time
import logging
import os
import platform
import sys
import struct
import threading
# import asyncio
import queue
import json
import importlib
import copy

import mill_prot

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

        self.log = logging.getLogger('Millennium')
        self.log.info("Millennium starting")
        self.WHITE = 0
        self.BLACK = 1
        self.turn = self.WHITE
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
        self.is_new_game = False
        self.trans = None
        self.trque = queue.Queue()  # asyncio.Queue()
        self.mill_config = None
        self.connected = False
        self.position = None
        self.reference_position = None
        self.orientation = True
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
                if 'orientation' not in self.mill_config:
                    self.mill_config['orientation'] = True
                self.log.debug('Checking default configuration for board via {} at {}'.format(
                    self.mill_config['transport'], self.mill_config['address']))
                self.orientation = self.mill_config['orientation']
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
                            self.write_configuration()
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

    def write_configuration(self):
        self.mill_config['orientation'] = self.orientation
        try:
            with open("millennium_config.json", "w") as f:
                json.dump(self.mill_config, f)
        except Exception as e:
            self.log.error("Failed to save default configuration {} to {}: {}".format(
                self.mill_config, "millennium_config.json", e))

    def event_worker_thread(self, que):
        self.log.debug('Millennium worker thread started.')
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
                                            if self.orientation == True:
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
                                if self.orientation == True:
                                    self.log.info("Cable-left board detected.")
                                    self.orientation = False
                                    self.write_configuration()
                                    position_inv = copy.deepcopy(position)
                                    for x in range(8):
                                        for y in range(8):
                                            position[x][y] = position_inv[7-x][7-y]
                                else:
                                    self.log.info(
                                        "Cable-right board detected.")
                                    self.orientation = True
                                    self.write_configuration()
                                    position_inv = copy.deepcopy(position)
                                    for x in range(8):
                                        for y in range(8):
                                            position[x][y] = position_inv[7-x][7-y]
                            fen = self.position_to_fen(position)
                            sfen = self.short_fen(fen)

                            if sfen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                                if self.is_new_game is False:
                                    self.is_new_game is True
                                    cmd = {'new game': '', 'actor': 'eboard',
                                           'orientation': self.orientation}
                                    self.new_game(position)
                                    self.appque.put(cmd)
                            else:
                                self.is_new_game = False

                            self.position = position
                            if self.reference_position == None:
                                self.reference_position = position
                            self.show_delta(
                                self.reference_position, self.position)
                            # self.print_position_ascii(position)
                            self.appque.put({'fen': fen, 'actor': 'eboard'})
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
                    if msg[0] == 'w':
                        self.log.debug('got write-register reply')
                        if len(msg) == 7:
                            reg_cont = '{}->{}'.format(
                                msg[1]+msg[2], msg[3]+msg[4])
                            self.log.info(
                                'Register written: {}'.format(reg_cont))
                        else:
                            self.log.warning(
                                'Invalid length {} for write-register reply'.format(len(msg)))
                    if msg[0] == 'r':
                        self.log.debug('got read-register reply')
                        if len(msg) == 7:
                            reg_cont = '{}->{}'.format(
                                msg[1]+msg[2], msg[3]+msg[4])
                            self.log.info(
                                'Register content: {}'.format(reg_cont))
                        else:
                            self.log.warning(
                                'Invalid length {} for read-register reply'.format(len(msg)))

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
            self.legal_moves = None
            self.reference_position = pos
            self.set_led_off()
        return True

    def move_from(self, fen, legal_moves, color, eval_only=False):
        if eval_only is False:
            self.legal_moves = legal_moves
            self.turn = color
            self.reference_position = self.fen_to_position(fen)
            self.show_delta(self.reference_position, self.position)
        else:
            eval_position = self.fen_to_position(fen)
            self.show_delta(self.position, eval_position,
                            freq=0x15, ontime1=0x02, ontime2=0x01)

    def show_deltas(self, positions, freq):
        if len(positions) > 5:
            npos = 5
        else:
            npos = len(positions)
        dpos = [[0 for x in range(8)] for y in range(8)]
        for ply in range(npos-1):
            frame = ply*2
            for y in range(8):
                for x in range(8):
                    if positions[ply+1][y][x] != positions[ply][y][x]:
                        if positions[ply][y][x] != 0:
                            dpos[y][x] |= 1 << (7 - frame)
                        else:
                            dpos[y][x] |= 1 << (7 - (frame + 1))
        self.set_mv_led(dpos, freq)
        time.sleep(0.05)

    def set_mv_led(self, pos, freq):
        if self.connected is True:
            leds = [[0 for x in range(9)] for y in range(9)]
            cmd = "L"+mill_prot.hex2(freq)
            for y in range(8):
                for x in range(8):
                    if pos[y][x] != 0:
                        if self.orientation == True:
                            leds[7-x][y] |= pos[y][x]
                            leds[7-x+1][y] |= pos[y][x]
                            leds[7-x][y+1] |= pos[y][x]
                            leds[7-x+1][y+1] |= pos[y][x]
                        else:
                            leds[x][7-y] |= pos[y][x]
                            leds[x+1][7-y] |= pos[y][x]
                            leds[x][7-y+1] |= pos[y][x]
                            leds[x+1][7-y+1] |= pos[y][x]

            for y in range(9):
                for x in range(9):
                    cmd = cmd + mill_prot.hex2(leds[y][x])
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    def show_delta(self, pos1, pos2, freq=0x20, ontime1=0x0f, ontime2=0xf0):
        dpos = [[0 for x in range(8)] for y in range(8)]
        for y in range(8):
            for x in range(8):
                if pos2[y][x] != pos1[y][x]:
                    if pos1[y][x] != 0:
                        dpos[y][x] = 1
                    else:
                        dpos[y][x] = 2
        self.set_led(dpos, freq, ontime1, ontime2)

    def set_led(self, pos, freq, ontime1, ontime2):
        if self.connected is True:
            leds = [[0 for x in range(9)] for y in range(9)]
            cmd = "L"+mill_prot.hex2(freq)
            for y in range(8):
                for x in range(8):
                    if pos[y][x] != 0:
                        if self.orientation == True:
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
                        cmd = cmd + mill_prot.hex2(ontime1)
                    else:
                        cmd = cmd + mill_prot.hex2(ontime2)

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

    def get_debounce(self):
        cmd = "R"+mill_prot.hex2(2)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    def set_debounce(self, count):
        cmd = "W02"
        if count < 0 or count > 4:
            self.log.error(
                'Invalid debounce count {}, should be 0: no debounce, 1 .. 4: 1-4  scan times debounce'.format(count))
        else:
            # 3: no debounce, 4: 2 scans debounce, -> 7: 4 scans
            cmd += mill_prot.hex2(count+3)
            self.trans.write_mt(cmd)
            self.log.debug("Setting board scan debounce to {}".format(count))

    def get_led_brightness_precent(self):
        cmd = "R"+mill_prot.hex2(4)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    def set_led_brightness(self, level=1.0):
        cmd = "W04"
        if level < 0.0 or level > 1.0:
            self.log.error(
                'Invalid brightness level {}, shouldbe between 0(darkest)..1.0(brightest)'.format(level))
        else:
            ilevel = int(level*15)
            cmd += mill_prot.hex2(ilevel)
            self.trans.write_mt(cmd)
            self.log.debug(
                "Setting led brightness to {} (bri={})".format(ilevel, level))

    def get_scan_time_ms(self):
        cmd = "R"+mill_prot.hex2(1)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Millennium board.")

    # default is scan every 40.96 ms, 24.4 scans per second.
    def set_scan_time_ms(self, scan_ms=41):
        cmd = "W01"
        if scan_ms < 2.048 * 15.0 or scan_ms > 255.0 * 2.048:
            self.log.error(
                'Invalid scan_ms {}, shouldbe between 30.72(fastest, might not work)..522.24(slowest, about 2 scans per sec))'.format(scan_ms))
        else:
            iscans = int(scan_ms/2.048)
            if iscans < 15:
                iscans = 15
            if iscans > 255:
                iscans = 255
            cmd += mill_prot.hex2(iscans)
            self.trans.write_mt(cmd)
            self.log.info(
                "Setting scan_ms intervall to {} -> {}ms ({} scans per sec)".format(iscans, scan_ms, 1000.0/scan_ms))

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
        fen += ' w '
        castle = ''
        if position[0][4] == 6 and position[0][7] == 4:
            castle += "K"
        if position[0][4] == 6 and position[0][0] == 4:
            castle += "Q"
        if position[7][4] == -6 and position[7][7] == -4:
            castle += "k"
        if position[7][4] == -6 and position[7][0] == -4:
            castle += "q"
        if castle == '':
            castle = '-'
        fen += castle+' - 0 1'
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

    def print_position_ascii(self, position, col, use_unicode_chess_figures=True, cable_pos=True):
        if cable_pos is True:
            fil = "  "
        else:
            fil = ""
        print("{}  +------------------------+".format(fil))
        for y in range(8):
            prf = ""
            pof = ""
            if cable_pos is True:
                prf = fil
                if y == 4:
                    if self.orientation == False:
                        prf = "=="
                    else:
                        pof = "=="

            print("{}{} |".format(prf, 8-y), end="")
            for x in range(8):
                f = position[7-y][x]
                if use_unicode_chess_figures is True:
                    if (x+y) % 2 == 0:
                        f = f*-1
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        if use_unicode_chess_figures is True:
                            c = self.figrep['unic'][i]
                        else:
                            c = self.figrep['ascii'][i]
                            if c == '.':
                                c = ' '
                        break
                if (x+y) % 2 == 0:
                    print("\033[7m {} \033[m".format(c), end="")
                else:
                    print(" {} ".format(c), end='')
            print("|{}".format(pof))
        print("{}  +------------------------+".format(fil))
        if col == self.WHITE:
            scol = 'white'
        else:
            scol = 'black'
        print("{}    A  B  C  D  E  F  G  H    ({})".format(fil, scol))

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

    def reset(self):
        if self.connected is True:
            self.trans.write_mt("T")
            self.log.warning(
                "Millennium board reset initiated, will take 3 secs.")
        else:
            self.log.warning(
                "Not connected to Millennium board, can't reset.")
        return '?'

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

    def set_orientation(self, orientation):
        self.orientation = orientation
        self.write_configuration()

    def get_orientation(self):
        return self.orientation


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

    def variant_to_positions(self, ebrd, cbrd, variant, plys):
        pos = []
        mvs = len(variant)
        if mvs > plys:
            mvs = plys

        pos.append(ebrd.fen_to_position(cbrd.fen()))
        for i in range(mvs):
            cbrd.push(chess.Move.from_uci(variant[i]))
            pos.append(ebrd.fen_to_position(cbrd.fen()))
        for i in range(mvs):
            cbrd.pop()
        return pos

    def color(self, ebrd, col):
        if col == chess.WHITE:
            col = ebrd.WHITE
        else:
            col = ebrd.BLACK
        return col

    def visualize_variant(self, ebrd, cbrd, variant, plys=1, freq=80):
        if plys > 4:
            plys = 4
        pos = self.variant_to_positions(ebrd, cbrd, variant, plys)
        ebrd.show_deltas(pos, freq)

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

        def score(self, cp, mate, lowerbound, upperbound):
            self.que.put({'score': {'cp': cp, 'mate': mate}})
            super().score(cp, mate, lowerbound, upperbound)

        def pv(self, moves):
            variant = []
            svar = ""
            for m in moves:
                variant.append(m.uci())
                svar += m.uci()+" "
            if svar[-1] == " ":
                svar = svar[:-1]
            self.que.put({'curmove': {
                'variant': variant,
                'variant string': svar,
                'actor': 'uci-engine'
            }})
            super().pv(moves)

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
                    self.kbd_moves = []
                    appque.put(
                        {'move': {'uci': cmd, 'actor': 'keyboard'}})
                elif cmd == 'n':
                    log.info('requesting new game')
                    appque.put({'new game': '', 'actor': 'keyboard'})
                elif cmd == 'b':
                    log.info('move back')
                    appque.put({'back': '', 'actor': 'keyboard'})
                elif cmd == 'c':
                    log.info('change board orientation')
                    appque.put(
                        {'turn eboard orientation': '', 'actor': 'keyboard'})
                elif cmd == 'a':
                    log.info('analyze')
                    appque.put({'analyze': '', 'actor': 'keyboard'})
                elif cmd == 'ab':
                    log.info('analyze black')
                    appque.put({'analyze': 'black', 'actor': 'keyboard'})
                elif cmd == 'aw':
                    log.info('analyze white')
                    appque.put({'analyze': 'white', 'actor': 'keyboard'})
                elif cmd == 'e':
                    log.info('board encoding switch')
                    appque.put({'encoding': '', 'actor': 'keyboard'})
                elif cmd[:2] == 'l ':
                    log.info('level')
                    movetime = float(cmd[2:])
                    appque.put({'level': '', 'movetime': movetime})
                elif cmd == 'p':
                    log.info('position')
                    appque.put({'position': '', 'actor': 'keyboard'})
                elif cmd == 'g':
                    log.info('go')
                    appque.put({'go': 'current', 'actor': 'keyboard'})
                elif cmd == 'gw':
                    log.info('go')
                    appque.put({'go': 'white', 'actor': 'keyboard'})
                elif cmd == 'gb':
                    log.info('go, black')
                    appque.put({'go': 'black', 'actor': 'keyboard'})
                elif cmd[:2] == 'h ':
                    log.info('show analysis for n plys (max 4) on board.')
                    ply = int(cmd[2:])
                    if ply < 0:
                        ply = 0
                    if ply > 4:
                        ply = 4
                    appque.put({'hint': '', 'ply': ply})

                elif cmd == 's':
                    log.info('stop')
                    appque.put({'stop': '', 'actor': 'keyboard'})
                elif cmd[:4] == 'fen ':
                    appque.put({'fen': cmd[4:], 'actor': 'keyboard'})
                elif cmd == 'help':
                    log.info(
                        'a - analyze current position, ab: analyze black, aw: analyses white')
                    log.info(
                        'c - change cable orientation (eboard cable left/right')
                    log.info('b - take back move')
                    log.info('g - go, current player (default white)')
                    log.info('gw - go, force white move')
                    log.info('gb - go, force black move')
                    log.info('h <ply> - show hints for <ply> levels on board')
                    log.info('l <n> - level: engine think-time in sec (float)')
                    log.info('n - new game')
                    log.info('p - import eboard position')
                    log.info('s - stop')
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


def write_preferences(prefs):
    try:
        with open("preferences.json", "w") as f:
            json.dump(prefs, f)
    except Exception as e:
        logging.error("Failed to write preferences.json, {}".format(e))


if __name__ == '__main__':
    import chess
    import chess.uci

    try:
        with open("preferences.json", "r") as f:
            prefs = json.load(f)
    except:
        prefs = {
            'think_ms': 3000,
            'use_unicode_figures': True,
        }
        write_preferences(prefs)

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
        engine_no = 0
        engine = chess.uci.popen_engine(bhlp.engines[engine_no]['path'])
        logging.info('Engine {} active.'.format(
            bhlp.engines[engine_no]['name']))
        engine.uci()
        # options
        engine.isready()
        bhlp.uci_handler(engine)
    else:
        engine = None

    if brd.connected is True:
        brd.get_version()
        time.sleep(0.1)
        brd.set_debounce(4)
        time.sleep(0.1)
        brd.get_scan_time_ms()
        time.sleep(0.1)
        brd.set_scan_time_ms(100.0)
        time.sleep(0.1)
        brd.get_scan_time_ms()
        time.sleep(0.1)
        init_position = True
        brd.get_position()
        ana_mode = False
        hint_ply = 1

        while True:
            if appque.empty() is False:
                msg = appque.get()
                appque.task_done()
                logging.debug("App received msg: {}".format(msg))
                if 'new game' in msg:
                    ana_mode = False
                    logging.info("New Game (by: {})".format(msg['actor']))
                    cbrd = chess.Board()
                    brd.print_position_ascii(brd.fen_to_position(
                        cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'])
                    vals = bhlp.valid_moves(cbrd)
                    bhlp.set_keyboard_valid(vals)
                    brd.move_from(cbrd.fen(), vals, bhlp.color(brd, cbrd.turn))
                if 'move' in msg:
                    if ana_mode == True and msg['move']['actor'] == 'uci-engine':
                        engine.position(cbrd)
                        engine.go(infinite=True, async_callback=True)
                        continue
                    uci = msg['move']['uci']
                    logging.info("{} move: {}".format(
                        msg['move']['actor'], uci))
                    ft = engine.stop(async_callback=True)
                    ft.result()
                    time.sleep(0.2)
                    mv = chess.Move.from_uci(uci)
                    cbrd.push(mv)
                    brd.print_position_ascii(brd.fen_to_position(
                        cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'])
                    if cbrd.is_check() and not cbrd.is_checkmate():
                        logging.info("Check!")
                    if cbrd.is_checkmate():
                        logging.info("Checkmate!")
                        if msg['move']['actor'] != 'eboard':
                            brd.move_from(cbrd.fen(), {},
                                          bhlp.color(brd, cbrd.turn))
                    else:
                        if msg['move']['actor'] == 'keyboard':
                            if ana_mode == True:
                                vals = bhlp.valid_moves(cbrd)
                                brd.move_from(cbrd.fen(), vals,
                                              bhlp.color(brd, cbrd.turn))
                                bhlp.set_keyboard_valid(vals)
                            else:
                                brd.move_from(cbrd.fen(), {},
                                              bhlp.color(brd, cbrd.turn))
                                bhlp.set_keyboard_valid(None)
                                engine.position(cbrd)
                                engine.go(movetime=prefs['think_ms'],
                                          async_callback=True)
                        if msg['move']['actor'] == 'eboard':
                            if ana_mode == True:
                                vals = bhlp.valid_moves(cbrd)
                                brd.move_from(cbrd.fen(), vals,
                                              bhlp.color(brd, cbrd.turn))
                                bhlp.set_keyboard_valid(vals)
                                for v in vals:
                                    print('{} '.format(vals[v]), end="")
                                print(' {}'.format(brd.turn))
                            else:
                                brd.move_from(cbrd.fen(), {},
                                              bhlp.color(brd, cbrd.turn))
                                bhlp.set_keyboard_valid(None)
                                engine.position(cbrd)
                                engine.go(movetime=prefs['think_ms'],
                                          async_callback=True)
                        if msg['move']['actor'] == 'uci-engine':
                            vals = bhlp.valid_moves(cbrd)
                            bhlp.set_keyboard_valid(vals)
                            brd.move_from(cbrd.fen(), vals,
                                          bhlp.color(brd, cbrd.turn))
                if 'go' in msg:
                    if msg['go'] == 'white':
                        cbrd.turn = chess.WHITE
                    if msg['go'] == 'black':
                        cbrd.turn = chess.BLACK
                    bhlp.set_keyboard_valid(None)
                    engine.position(cbrd)
                    engine.go(movetime=prefs['think_ms'], async_callback=True)
                if 'analyze' in msg:
                    if msg['analyze'] == 'white':
                        cbrd.turn = chess.WHITE
                    if msg['analyze'] == 'black':
                        cbrd.turn = chess.BLACK
                    ana_mode = True
                    vals = bhlp.valid_moves(cbrd)
                    brd.move_from(cbrd.fen(), vals, bhlp.color(brd, cbrd.turn))
                    bhlp.set_keyboard_valid(vals)
                    engine.position(cbrd)
                    engine.go(infinite=True, async_callback=True)
                if 'stop' in msg:
                    engine.stop()
                    time.sleep(0.2)
                    ana_mode = False
                    vals = bhlp.valid_moves(cbrd)
                    brd.move_from(cbrd.fen(), vals, bhlp.color(brd, cbrd.turn))
                    bhlp.set_keyboard_valid(vals)
                if 'back' in msg:
                    cbrd.pop()
                    brd.print_position_ascii(brd.fen_to_position(
                        cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'])
                    if cbrd.is_check() and not cbrd.is_checkmate():
                        logging.info("Check!")
                    vals = bhlp.valid_moves(cbrd)
                    brd.move_from(cbrd.fen(), vals, bhlp.color(brd, cbrd.turn))
                    bhlp.set_keyboard_valid(vals)
                    if ana_mode:
                        engine.position(cbrd)
                        engine.go(infinite=True, async_callback=True)
                if 'curmove' in msg:
                    uci = msg['curmove']['variant']
                    logging.info("{} variant: {}".format(
                        msg['curmove']['actor'], msg['curmove']['variant string']))
                    bhlp.visualize_variant(
                        brd, cbrd, msg['curmove']['variant'], hint_ply, 50)
                if 'score' in msg:
                    if msg['score']['mate'] is not None:
                        logging.info('Mate in {}'.format(msg['score']['mate']))
                    else:
                        logging.info('Score {}'.format(msg['score']['cp']))
                if 'fen' in msg:
                    if msg['actor'] == 'keyboard' or (msg['actor'] == 'eboard' and init_position is True):
                        init_position = False
                        cbrd = chess.Board(msg['fen'])
                        if cbrd.is_valid() is True:
                            brd.print_position_ascii(brd.fen_to_position(
                                cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'])
                            vals = bhlp.valid_moves(cbrd)
                            bhlp.set_keyboard_valid(vals)
                            brd.move_from(cbrd.fen(), vals,
                                          bhlp.color(brd, cbrd.turn))
                        else:
                            logging.error(
                                'Invalid FEN position {}, starting new game.'.format(msg['fen']))
                            appque.put(
                                {'new game': '', 'actor': 'bad position error'})
                if 'position' in msg:
                    init_position = True
                    brd.get_position()
                if 'encoding' in msg:
                    prefs['use_unicode_figures'] = not prefs['use_unicode_figures']
                    write_preferences(prefs)
                    brd.print_position_ascii(brd.fen_to_position(
                        cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'])

                if 'level' in msg:
                    if 'movetime' in msg:
                        prefs['think_ms'] = int(msg['movetime']*1000)
                        logging.info(
                            'Engine move time is {} ms'.format(prefs['think_ms']))
                        write_preferences(prefs)
                if 'hint' in msg:
                    if 'ply' in msg:
                        hint_ply = msg['ply']
                if 'turn eboard orientation' in msg:
                    if brd.get_orientation() is False:
                        brd.set_orientation(True)
                        logging.info("eboard cable on right side.")
                    else:
                        brd.set_orientation(False)
                        logging.info("eboard cable on left side.")
                    init_position = True
                    brd.get_position()
            else:
                # if brd.trans.get_name() == 'millcon_bluepy_ble':
                #     if brd.trans.blemutex.locked() is False:
                #         brd.trans.blemutex.acquire()
                #         brd.trans.mil.waitForNotifications(1.0)
                #         brd.trans.blemutex.release()
                time.sleep(0.1)
