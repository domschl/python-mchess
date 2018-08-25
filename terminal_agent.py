import logging
import time
import sys
import platform
import threading
import queue

import chess


class TerminalAgent:
    def __init__(self, appque):
        self.name = 'TerminalAgent'
        self.log = logging.getLogger("TerminalAgent")
        self.appque = appque
        self.orientation = True

        self.kbd_moves = []
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        # TODO: this seems to set windows terminal to Unicode. There should be a better way.
        if platform.system().lower() == 'windows':
            from ctypes import windll, c_int, byref
            stdout_handle = windll.kernel32.GetStdHandle(c_int(-11))
            mode = c_int(0)
            windll.kernel32.GetConsoleMode(c_int(stdout_handle), byref(mode))
            mode = c_int(mode.value | 4)
            windll.kernel32.SetConsoleMode(c_int(stdout_handle), mode)

    def agent_ready(self):
        return True

    def print_position_ascii(self, position, col, use_unicode_chess_figures=True, cable_pos=True, move_stack=[]):
        if cable_pos is True:
            fil = "  "
        else:
            fil = ""
        if move_stack == []:
            move_stack = ["" for _ in range(11)]
        print(
            "{}  +------------------------+     {}".format(fil, move_stack[0]))
        for y in range(8):
            prf = ""
            pof = "  "
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
            print("|{}   {}".format(pof, move_stack[y+1]))
        print(
            "{}  +------------------------+     {}".format(fil, move_stack[9]))
        print("{}    A  B  C  D  E  F  G  H       {}".format(
            fil, move_stack[10]))

    def ascii_move_stack(self, cbrd, score, use_unicode_chess_figures=True, lines=11):
        ams = ["" for _ in range(11)]
        mc = len(cbrd.move_stack)
        if cbrd.turn == chess.BLACK:
            mmc = 2*lines-1
        else:
            mmc = 2*lines
        if mc > mmc:
            mc = mmc
        move_store = []

        amsi = lines-1
        for i in range(mc):
            if amsi < 0:
                logging.error("bad amsi index! {}".format(amsi))
            if cbrd.is_checkmate() is True:
                if use_unicode_chess_figures is True:
                    chk = self.chesssym['unic'][3]
                else:
                    chk = self.chesssym['ascii'][3]
            elif cbrd.is_check() is True:
                if use_unicode_chess_figures is True:
                    chk = self.chesssym['unic'][2]
                else:
                    chk = self.chesssym['ascii'][2]
            else:
                chk = ""
            l1 = len(cbrd.piece_map())
            mv = cbrd.pop()
            l2 = len(cbrd.piece_map())
            move_store.append(mv)
            if l1 != l2:  # capture move, piece count changed :-/
                if use_unicode_chess_figures is True:
                    sep = self.chesssym['unic'][1]
                else:
                    sep = self.chesssym['ascii'][1]
            else:
                if use_unicode_chess_figures is True:
                    sep = self.chesssym['unic'][0]
                else:
                    sep = self.chesssym['ascii'][0]
            if mv.promotion is not None:
                fig = chess.Piece(chess.PAWN, cbrd.piece_at(
                    mv.from_square).color).unicode_symbol(invert_color=True)
                if use_unicode_chess_figures is True:
                    pro = chess.Piece(mv.promotion, cbrd.piece_at(
                        mv.from_square).color).unicode_symbol(invert_color=True)
                else:
                    pro = mv.promotion.symbol()
            else:
                pro = ""
                if use_unicode_chess_figures is True:
                    fig = cbrd.piece_at(mv.from_square).unicode_symbol(
                        invert_color=True)
                else:
                    fig = cbrd.piece_at(mv.from_square).symbol()
            move = '{:10s}'.format(
                fig+" "+chess.SQUARE_NAMES[mv.from_square]+sep+chess.SQUARE_NAMES[mv.to_square]+pro+chk)
            if amsi == lines-1 and score != '':
                move = '{} ({})'.format(move, score)
                score = ''

            ams[amsi] = move + ams[amsi]
            if cbrd.turn == chess.WHITE:
                amsi = amsi-1

        for i in reversed(range(len(move_store))):
            cbrd.push(move_store[i])

        return ams

    def set_valid_moves(self, board, vals):
        self.kbd_moves = []
        if vals != None:
            for v in vals:
                self.kbd_moves.append(vals[v])

    def kdb_event_worker_thread(self, appque, log, std_in):
        while self.kdb_thread_active:
            cmd = ""
            try:
                # cmd = input()
                # with open(std_in) as inp:
                cmd = std_in.readline().strip()
            except Exception as e:
                log.info("Exception in input() {}".format(e))
                time.sleep(1.0)
            if cmd == "":
                continue
            log.debug("keyboard: <{}>".format(cmd))
            if len(cmd) >= 1:
                if cmd in self.kbd_moves:
                    self.kbd_moves = []
                    appque.put(
                        {'move': {'uci': cmd, 'actor': 'keyboard'}})
                elif cmd == 'n':
                    log.debug('requesting new game')
                    appque.put({'new game': '', 'actor': 'keyboard'})
                elif cmd == 'b':
                    log.debug('move back')
                    appque.put({'back': '', 'actor': 'keyboard'})
                elif cmd == 'c':
                    log.debug('change board orientation')
                    appque.put(
                        {'turn eboard orientation': '', 'actor': 'keyboard'})
                elif cmd == 'a':
                    log.debug('analyze')
                    appque.put({'analyze': '', 'actor': 'keyboard'})
                elif cmd == 'ab':
                    log.debug('analyze black')
                    appque.put({'analyze': 'black', 'actor': 'keyboard'})
                elif cmd == 'aw':
                    log.debug('analyze white')
                    appque.put({'analyze': 'white', 'actor': 'keyboard'})
                elif cmd == 'e':
                    log.debug('board encoding switch')
                    appque.put({'encoding': '', 'actor': 'keyboard'})
                elif cmd[:2] == 'l ':
                    log.debug('level')
                    movetime = float(cmd[2:])
                    appque.put({'level': '', 'movetime': movetime})
                elif cmd[:2] == 'm ':
                    log.debug('max ply look-ahead display')
                    n = int(cmd[2:])
                    appque.put({'max_ply': n})
                elif cmd == 'p':
                    log.debug('position')
                    appque.put({'position': '', 'actor': 'keyboard'})
                elif cmd == 'g':
                    log.debug('go')
                    appque.put({'go': 'current', 'actor': 'keyboard'})
                elif cmd == 'gw':
                    log.debug('go')
                    appque.put({'go': 'white', 'actor': 'keyboard'})
                elif cmd == 'gb':
                    log.debug('go, black')
                    appque.put({'go': 'black', 'actor': 'keyboard'})
                elif cmd == 'w':
                    appque.put({'write_prefs': ''})
                elif cmd[:2] == 'h ':
                    log.debug('show analysis for n plys (max 4) on board.')
                    ply = int(cmd[2:])
                    if ply < 0:
                        ply = 0
                    if ply > 4:
                        ply = 4
                    appque.put({'hint': '', 'ply': ply})

                elif cmd == 's':
                    log.debug('stop')
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
                    log.info('m <n> - max plys shown during look-ahead')
                    log.info('n - new game')
                    log.info('p - import eboard position')
                    log.info('s - stop')
                    log.info('w - write current prefences as default')
                    log.info('e2e4 - valid move')
                else:
                    log.info(
                        'Unknown keyboard cmd <{}>, enter "help" for a list of valid commands.'.format(cmd))

    def keyboard_handler(self):
        self.kdb_thread_active = True
        self.kbd_event_thread = threading.Thread(
            target=self.kdb_event_worker_thread, args=(self.appque, self.log, sys.stdin))
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()
