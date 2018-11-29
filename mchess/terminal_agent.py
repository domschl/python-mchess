import logging
import time
import sys
import platform
import threading
import queue
import copy

import chess


class TerminalAgent:
    def __init__(self, appque, prefs):
        self.name = 'TerminalAgent'
        self.prefs = prefs
        self.log = logging.getLogger("TerminalAgent")
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

        self.keyboard_handler()

    def agent_ready(self):
        return self.active

    def quit(self):
        for _ in range(self.last_cursor_up):
            print()
        self.kdb_thread_active = False

    def position_to_text(self, brd, use_unicode_chess_figures=True, invert=False):
        board = copy.deepcopy(brd)
        tpos = []
        tpos.append(
            "  +------------------------+")
        for y in reversed(range(8)):
            ti = "{} |".format(y+1)
            for x in range(8):
                f = board.piece_at(chess.square(x, y))
                if (x+y) % 2 == 0 and use_unicode_chess_figures is True:
                    invinv = invert
                else:
                    invinv = not invert
                c = '?'
                # for i in range(len(self.figrep['int'])):
                if f == None:
                    c = ' '
                else:
                    if use_unicode_chess_figures is True:
                        c = f.unicode_symbol(invert_color=invinv)
                    else:
                        c = f.symbol()
                    # if ((self.figrep['pythc'][i][1] == f.color) == inv) and self.figrep['pythc'][i][0] == f.piece_type:
                    #     if use_unicode_chess_figures is True:
                    #         c = self.figrep['unic'][i]
                    #     else:
                    #         c = self.figrep['ascii'][i]
                    # break
                if (x+y) % 2 == 0:
                    ti += "\033[7m {} \033[m".format(c)
                else:
                    ti += " {} ".format(c)
            ti += "|"
            tpos.append(ti)
        tpos.append(
            "  +------------------------+")
        tpos.append("    A  B  C  D  E  F  G  H  ")
        return tpos

    def moves_to_text(self, brd, score=None, use_unicode_chess_figures=True, invert=False, lines=11):
        board = copy.deepcopy(brd)
        ams = ["" for _ in range(11)]
        mc = len(board.move_stack)
        if board.turn == chess.BLACK:
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
            if board.is_checkmate() is True:
                if use_unicode_chess_figures is True:
                    chk = self.chesssym['unic'][3]
                else:
                    chk = self.chesssym['ascii'][3]
            elif board.is_check() is True:
                if use_unicode_chess_figures is True:
                    chk = self.chesssym['unic'][2]
                else:
                    chk = self.chesssym['ascii'][2]
            else:
                chk = ""
            l1 = len(board.piece_map())
            mv = board.pop()
            if mv == chess.Move.null():
                move = '{:10s}'.format('--')
            else:
                l2 = len(board.piece_map())
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
                    # TODO: cleanup fig-code generation
                    try:
                        fig = chess.Piece(chess.PAWN, board.piece_at(
                            mv.from_square).color).unicode_symbol(invert_color=True)
                    except Exception as e:
                        self.log.error(
                            "Move contains empty origin: {}".format(e))
                        fig = "?"
                    if use_unicode_chess_figures is True:
                        try:
                            pro = chess.Piece(mv.promotion, board.piece_at(
                                mv.from_square).color).unicode_symbol(invert_color=True)
                        except Exception as e:
                            self.log.error(
                                "Move contains empty origin: {}".format(e))
                            fig = "?"
                    else:
                        try:
                            pro = mv.promotion.symbol()
                        except Exception as e:
                            self.log.error(
                                "Move contains empty origin: {}".format(e))
                            fig = "?"
                else:
                    pro = ""
                    if use_unicode_chess_figures is True:
                        try:
                            fig = board.piece_at(mv.from_square).unicode_symbol(
                                invert_color=not invert)
                        except Exception as e:
                            self.log.error(
                                "Move contains empty origin: {}".format(e))
                            fig = "?"
                    else:
                        try:
                            fig = board.piece_at(mv.from_square).symbol()
                        except Exception as e:
                            self.log.error(
                                "Move contains empty origin: {}".format(e))
                            fig = "?"
                move = '{:10s}'.format(
                    fig+" "+chess.SQUARE_NAMES[mv.from_square]+sep+chess.SQUARE_NAMES[mv.to_square]+pro+chk)

            if amsi == lines-1 and score != None:
                move = '{} ({})'.format(move, score)
                score = ''

            ams[amsi] = move + ams[amsi]
            if board.turn == chess.WHITE:
                ams[amsi] = "{:3d}. ".format(board.fullmove_number) + ams[amsi]
                amsi = amsi-1

        for i in reversed(range(len(move_store))):
            board.push(move_store[i])

        return ams

    def cursor_up(self, n=1):
        # Windows: cursor up by n:   ESC [ <n> A
        # ANSI:    cursor up by n:   ESC [ <n> A
        # ESC=\033, 27
        esc = chr(27)
        print("{}[{}A".format(esc, n), end="")

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        txa = self.position_to_text(
            board, use_unicode_chess_figures=attribs['unicode'], invert=attribs['invert'])
        ams = self.moves_to_text(board, lines=len(
            txa), use_unicode_chess_figures=attribs['unicode'], invert=attribs['invert'])
        header = '                                {:>10.10s} - {:10.10s}'.format(
            attribs['white_name'], attribs['black_name'])
        new_cache = header
        for i in range(len(txa)):
            col = '  '
            if (board.turn == chess.WHITE) and (i == 8):
                col = '<-'
            if (board.turn == chess.BLACK) and (i == 1):
                col = '<-'
            new_cache += '{}{}{}'.format(txa[i], col, ams[i])
        if new_cache == self.display_cache:
            self.log.debug("Unnecessary display_board call")
            return
        self.display_cache = new_cache
        print(header)
        for i in range(len(txa)):
            col = '  '
            if (board.turn == chess.WHITE) and (i == 8):
                col = '<-'
            if (board.turn == chess.BLACK) and (i == 1):
                col = '<-'
            print('{}{}{}'.format(txa[i], col, ams[i]))

    def agent_states(self, msg):
        print('State of agent {} changed to {}, {}'.format(
            msg['actor'], msg['agent-state'], msg['message']))

    def display_move(self, move_msg):
        if 'score' in move_msg['move']:
            new_move = '\nMove {} (ev: {}) by {}'.format(
                move_msg['move']['uci'], move_msg['move']['score'], move_msg['move']['actor'])
        else:
            new_move = '\nMove {} by {}'.format(
                move_msg['move']['uci'], move_msg['move']['actor'])
        if 'ponder' in move_msg['move']:
            new_move += '\nPonder: {}'.format(move_msg['move']['ponder'])

        if new_move != self.move_cache:
            for _ in range(self.last_cursor_up):
                print()
            self.last_cursor_up = 0
            self.move_cache = new_move
            print(new_move)
            print()
        else:
            self.log.debug(
                "Unnecessary repetion of move-print suppressed by cache")
        self.info_cache = ""
        self.info_provider = {}
        self.max_mpv = 1
        for ac in self.info_provider:
            self.info_provider[ac] = {}

    def display_info(self, board, info):
        mpv_ind = info['multipv_ind']  # index to multipv-line number 1..
        if mpv_ind > self.max_mpv:
            self.max_mpv = mpv_ind

        header = '['
        if 'actor' in info:
            header += info['actor']+' '
        if 'nps' in info:
            header += 'Nps: {} '.format(info['nps'])
        if 'depth' in info:
            d = 'Depth: {}'.format(info['depth'])
            if 'seldepth' in info:
                d += '/{} '.format(info['seldepth'])
            header += d
        if 'appque' in info:
            header += 'AQue: {} '.format(info['appque'])
        if 'tbhits' in info:
            header += 'TB: {}] '.format(info['tbhits'])
        else:
            header += '] '

        variant = '({}) '.format(mpv_ind)
        if 'score' in info:
            variant += '{}  '.format(info['score'])
        if 'variant' in info:
            moves = info['variant']
            mvs = len(moves)
            if mvs > self.max_plies:
                mvs = self.max_plies
            for i in range(mvs):
                if i > 0:
                    variant += ' '
                variant += moves[i].uci()

        if info['actor'] not in self.info_provider:
            self.info_provider[info['actor']] = {}
        self.info_provider[info['actor']]['header'] = header
        self.info_provider[info['actor']][mpv_ind] = variant

        cst = ""
        for ac in self.info_provider:
            for k in self.info_provider[ac]:
                cst += self.info_provider[ac][k]
        if cst != self.info_cache:
            self.info_cache = cst
            n = 0
            for ac in self.info_provider:
                if 'header' not in self.info_provider[ac]:
                    continue
                print('{:80s}'.format(self.info_provider[ac]['header'][:80]))
                n += 1
                for i in range(1, self.max_mpv+1):
                    if i in self.info_provider[ac]:
                        print('{:80s}'.format(self.info_provider[ac][i][:80]))
                        n += 1
            self.cursor_up(n)
            self.last_cursor_up = n
        else:
            self.log.debug("Suppressed redundant display_info")

    def set_valid_moves(self, board, vals):
        self.kbd_moves = []
        if vals != None:
            for v in vals:
                self.kbd_moves.append(vals[v])

    def kdb_event_worker_thread(self, appque, log, std_in):
        while self.kdb_thread_active:
            self.active = True
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
                        {'move': {'uci': cmd, 'actor': self.name}})
                elif cmd == '--':
                    self.kbd_moves = []
                    appque.put(
                        {'move': {'uci': '0000', 'actor': self.name}})
                elif cmd == 'a':
                    log.debug('analyze')
                    appque.put({'analysis': '', 'actor': self.name})
                elif cmd == 'b':
                    log.debug('move back')
                    appque.put({'back': '', 'actor': self.name})
                elif cmd == 'c':
                    log.debug('change ChessLink board orientation')
                    appque.put(
                        {'turn eboard orientation': '', 'actor': self.name})
                elif cmd == 'e':
                    log.debug('board encoding switch')
                    appque.put({'encoding': '', 'actor': self.name})
                elif cmd == 'f':
                    log.debug('move forward')
                    appque.put({'forward': '', 'actor': self.name})
                elif cmd[:4] == 'fen ':
                    appque.put({'fen_setup': cmd[4:], 'actor': self.name})
                elif cmd == 'g':
                    log.debug('go')
                    appque.put({'go': 'current', 'actor': self.name})
                elif cmd[:2] == 'h ':
                    log.debug(
                        'show analysis for n plies (max 4) on ChessLink board.')
                    ply = int(cmd[2:])
                    if ply < 0:
                        ply = 0
                    if ply > 4:
                        ply = 4
                    appque.put({'led_hint': ply})
                elif cmd[:1] == 'm':
                    if len(cmd) == 4:
                        if cmd[2:] == "PP":
                            log.debug("mode: player-player")
                            appque.put({'game_mode': 'PLAYER_PLAYER'})
                        elif cmd[2:] == "PE":
                            log.debug("mode: player-engine")
                            appque.put({'game_mode': 'PLAYER_ENGINE'})
                        elif cmd[2:] == "EP":
                            log.debug("mode: engine-player")
                            appque.put({'game_mode': 'ENGINE_PLAYER'})
                        elif cmd[2:] == "EE":
                            log.debug("mode: engine-engine")
                            appque.put({'game_mode': 'ENGINE_ENGINE'})
                    else:
                        log.warning(
                            'Illegal m parameter, use: PP, PE, EP, EE (see help-command)')
                elif cmd == 'n':
                    log.debug('requesting new game')
                    appque.put({'new game': '', 'actor': self.name})
                elif cmd == 'p':
                    log.debug('position_fetch')
                    appque.put(
                        {'position_fetch': 'ChessLinkAgent', 'actor': self.name})
                elif cmd == 'q':
                    appque.put({'quit': '', 'actor': self.name})
                elif cmd == 's':
                    log.debug('stop')
                    appque.put({'stop': '', 'actor': self.name})
                elif cmd == 'tw':
                    log.debug('turn white')
                    appque.put({'turn': 'white', 'actor': self.name})
                elif cmd == 'tb':
                    log.debug('turn black')
                    appque.put({'turn': 'black', 'actor': self.name})

                elif cmd == 'help':
                    log.info('Terminal commands:')
                    log.info('e2e4 - enter a valid move (in UCI format)')
                    log.info('--  null move')
                    log.info('a - analyze current position')
                    log.info('b - take back move')
                    log.info(
                        'c - change cable orientation (eboard cable left/right')
                    log.info("fen <fen> - set board to <fen> position")
                    log.info(
                        'g - go, current player (default white) or force current move')
                    log.info('h <ply> - show hints for <ply> levels on board')
                    log.info(
                        'm <mode> - modes: PP: Player-Player, PE: Engine-Player, EP, EE.')
                    log.info('n - new game')
                    log.info('p - import ChessLink board position')
                    log.info('q - quit')
                    log.info('s - stop and discard calculation')
                    log.info('tw - next move: white')
                    log.info('tb - next move: black')
                else:
                    log.info(
                        'Unknown keyboard cmd <{}>, enter "help" for a list of valid commands.'.format(cmd))

    def keyboard_handler(self):
        self.kdb_thread_active = True
        self.kbd_event_thread = threading.Thread(
            target=self.kdb_event_worker_thread, args=(self.appque, self.log, sys.stdin))
        self.kbd_event_thread.setDaemon(True)
        self.kbd_event_thread.start()
