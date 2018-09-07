import time
import logging
import os
import platform
import sys
import struct
import threading
import queue
import json
import importlib
import copy

import chess_link_protocol as clp

# TODO: Expand protocol description
"""The Chess Link Protocol

<V56>
2018-08-31 11:07:31,141 DEBUG ChessLinkBluePy Sending: <b'\xd6\xb5\xb6'>
2018-08-31 11:07:31,212 DEBUG ChessLinkBluePy BLE: Handle: 55, data: b'v\xb01\xb0\xb374'
2018-08-31 11:07:31,212 DEBUG ChessLinkBluePy BLE received [v010374]
2018-08-31 11:07:31,212 DEBUG ChessLinkBluePy bluepy_ble received complete msg: v010374


"""


class ChessLink:
    """This implements the 'Chess Link' protocol for Millennium Chess Genius Exclusive and future boards compatible with that protocol"""

    def __init__(self, appque, name):
        """Constructor, searches, configures and connectors to Chess Link compatible Millennium Chess Genius Exclusive or similar boards.
        :param appque: a Queue that receive chess board events
        :param name: identifies this protocol"""
        self.name = name
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "ascii": "PNBRQK.pnbrqk"}
        self.transports = {'Darwin': ['chess_link_usb'], 'Linux': [
            'chess_link_bluepy', 'chess_link_usb'], 'Windows': ['chess_link_usb']}

        self.log = logging.getLogger('ChessLink')
        self.log.debug("Chess Link starting")
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
            self.log.debug(msg)
            exit(-1)

        self.appque = appque
        self.board_mutex = threading.Lock()
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
            target=self._event_worker_thread, args=(self.trque, self.board_mutex))
        self.event_thread.setDaemon(True)
        self.event_thread.start()

        try:
            with open("chess_link_config.json", "r") as f:
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
                            self.log.debug("Found board on transport {} at address {}".format(
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
            self.log.debug('Valid board available on {} at {}'.format(
                self.mill_config['transport'], self.mill_config['address']))
            if platform.system() != 'Windows':
                if os.geteuid() == 0:
                    self.log.warning(
                        'Do not run as root, once intial BLE scan is done.')
            self.log.debug('Connecting to Chess Link via {} at {}'.format(
                self.mill_config['transport'], self.mill_config['address']))
            self.connected = self.trans.open_mt(self.mill_config['address'])
            if self.connected is True:
                self.log.info('Connected to Chess Link via {} at {}'.format(
                    self.mill_config['transport'], self.mill_config['address']))
            else:
                self.log.error('Connection to Chess Link via {} at {} FAILED.'.format(
                    self.mill_config['transport'], self.mill_config['address']))

    def position_initialized(self):
        """Check, if a board position has been received and chess link board is online.
        :return: True, if board position has been received."""
        if self.connected is True:
            pos = None
            with self.board_mutex:
                pos = self.position
            if pos is not None:
                return True
        return False

    def write_configuration(self):
        """Write the configuration for hardware connection (USB/Bluetooth LE) 
        and board orientation to 'chess_link_config.json
        :return: True on success, False on error"""
        self.mill_config['orientation'] = self.orientation
        try:
            with open("chess_link_config.json", "w") as f:
                json.dump(self.mill_config, f)
                return True
        except Exception as e:
            self.log.error("Failed to save default configuration {} to {}: {}".format(
                self.mill_config, "chess_link_config.json", e))
        return False

    def _event_worker_thread(self, que, mutex):
        """This background thread is started on creation of a ChessLink object. 
        It decodes chess link encoded messages and sends jason messages to the application."""
        self.log.debug('Chess Link worker thread started.')
        while self.thread_active:
            if self.trque.empty() is False:
                msg = self.trque.get()
                if msg == 'error':
                    self.appque.put(
                        {'error': 'transport failure or not available.'})
                    continue

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
                                    self.log.debug(
                                        "Cable-left board detected.")
                                    self.orientation = False
                                    self.write_configuration()
                                    position_inv = copy.deepcopy(position)
                                    for x in range(8):
                                        for y in range(8):
                                            position[x][y] = position_inv[7-x][7-y]
                                else:
                                    self.log.debug(
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
                                    cmd = {'new game': '', 'actor': self.name,
                                           'orientation': self.orientation}
                                    self.new_game(position)
                                    self.appque.put(cmd)
                            else:
                                self.is_new_game = False

                            with mutex:
                                self.position = copy.deepcopy(position)
                                if self.reference_position == None:
                                    self.reference_position = copy.deepcopy(
                                        position)
                            self.show_delta(
                                self.reference_position, self.position)
                            # self.print_position_ascii(position)
                            self.appque.put({'fen': fen, 'actor': self.name})
                            self._check_move(position)
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
                            self.log.debug(
                                'Register written: {}'.format(reg_cont))
                        else:
                            self.log.warning(
                                'Invalid length {} for write-register reply'.format(len(msg)))
                    if msg[0] == 'r':
                        self.log.debug('got read-register reply')
                        if len(msg) == 7:
                            reg_cont = '{}->{}'.format(
                                msg[1]+msg[2], msg[3]+msg[4])
                            self.log.debug(
                                'Register content: {}'.format(reg_cont))
                        else:
                            self.log.warning(
                                'Invalid length {} for read-register reply'.format(len(msg)))

            else:
                time.sleep(0.01)

    def new_game(self, pos):
        """Initiate a new game
        :param pos: position array of the current position. If the hardware board has 
        currently a different position, all differences are indicated by blinking leds.
        """
        self.reference_position = pos
        self.set_led_off()
        self.legal_moves = None

    def _check_move(self, pos):
        """Check, if current change on board is a legal move. If yes, put move into queue"""
        fen = self.short_fen(self.position_to_fen(pos))
        if self.legal_moves is not None and fen in self.legal_moves:
            self.appque.put(
                {'move': {'uci': self.legal_moves[fen], 'fen': fen, 'actor': self.name}})
            self.legal_moves = None
            self.reference_position = pos
            self.set_led_off()
            return True
        return False

    def move_from(self, fen, legal_moves, color, eval_only=False):
        """Register all legal moves possible in current position.
        :param fen: current position
        :param legal_moves: dictionary of key:fen value: uci_move (e.g. e2e4)
        :param color: color to move
        :param eval_only: True: indicate ponder evals
        """
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
        """Signal leds to show difference between current position on board, and intended position. This is used
        to signal moves by other agents, or discrepancies with the current position."""
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
        """Set the leds on board according to pos array"""
        if self.connected is True:
            leds = [[0 for x in range(9)] for y in range(9)]
            cmd = "L"+clp.hex2(freq)
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
                    cmd = cmd + clp.hex2(leds[y][x])
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Chess Link.")

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
            cmd = "L"+clp.hex2(freq)
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
                        cmd = cmd + clp.hex2(ontime1)
                    else:
                        cmd = cmd + clp.hex2(ontime2)

            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Chess Link.")

    def set_led_off(self):
        if self.connected is True:
            self.trans.write_mt("X")
        else:
            self.log.warning(
                "Not connected to Chess Link.")

    def get_debounce(self):
        cmd = "R"+clp.hex2(2)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Chess Link.")

    def set_debounce(self, count):
        cmd = "W02"
        if count < 0 or count > 4:
            self.log.error(
                'Invalid debounce count {}, should be 0: no debounce, 1 .. 4: 1-4  scan times debounce'.format(count))
        else:
            # 3: no debounce, 4: 2 scans debounce, -> 7: 4 scans
            cmd += clp.hex2(count+3)
            self.trans.write_mt(cmd)
            self.log.debug("Setting board scan debounce to {}".format(count))

    def get_led_brightness_percent(self):
        cmd = "R"+clp.hex2(4)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Chess Link.")

    def set_led_brightness(self, level=1.0):
        cmd = "W04"
        if level < 0.0 or level > 1.0:
            self.log.error(
                'Invalid brightness level {}, shouldbe between 0(darkest)..1.0(brightest)'.format(level))
        else:
            ilevel = int(level*15)
            cmd += clp.hex2(ilevel)
            self.trans.write_mt(cmd)
            self.log.debug(
                "Setting led brightness to {} (bri={})".format(ilevel, level))

    def get_scan_time_ms(self):
        cmd = "R"+clp.hex2(1)
        if self.connected is True:
            self.trans.write_mt(cmd)
        else:
            self.log.warning(
                "Not connected to Chess Link.")

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
            cmd += clp.hex2(iscans)
            self.trans.write_mt(cmd)
            self.log.debug(
                "Setting scan_ms intervall to {} -> {}ms ({} scans per sec)".format(iscans, scan_ms, 1000.0/scan_ms))

    # TODO: move this?
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
                "Chess Link reset initiated, will take 3 secs.")
        else:
            self.log.warning(
                "Not connected to Chess Link, can't reset.")
        return '?'

    def get_version(self):
        if self.connected is True:
            self.trans.write_mt("V")
        else:
            self.log.warning(
                "Not connected to Chess Link, can't get version.")
        return '?'

    def get_position(self):
        if self.connected is True:
            self.trans.write_mt("S")
        else:
            self.log.warning(
                "Not connected to Chess Link, can't get position.")
        return '?'

    def set_orientation(self, orientation):
        self.orientation = orientation
        self.write_configuration()

    def get_orientation(self):
        return self.orientation
