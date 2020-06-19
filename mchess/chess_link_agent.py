''' Agent for Millennium chess board Chess Genius Exclusive '''
import logging
import time
import copy

import chess
import chess_link as cl


class ChessLinkAgent:
    ''' Hardware board agent implementation '''

    def __init__(self, appque, prefs, timeout=30):
        self.name = 'ChessLinkAgent'
        self.appque = appque
        self.prefs = prefs
        self.ply_vis_delay = prefs['ply_vis_delay']
        self.log = logging.getLogger(self.name)
        self.cl_brd = cl.ChessLink(appque, self.name)
        self.init_position = False

        if self.cl_brd.connected is True:
            self.cl_brd.get_version()
            self.cl_brd.set_debounce(4)
            self.cl_brd.get_scan_time_ms()
            self.cl_brd.set_scan_time_ms(100.0)
            self.cl_brd.get_scan_time_ms()
            self.cl_brd.get_position()
        else:
            self.log.warning("Connection to ChessLink failed.")
            return
        self.max_plies = 3

        self.log.debug("waiting for board position")
        start = time.time()
        warned = False
        while time.time()-start < timeout and self.init_position is False:
            if self.cl_brd.error_condition is True:
                self.log.info("ChessLink board not available.")
                return
            if time.time()-start > 2 and warned is False:
                warned = True
                self.log.info(
                    f"Searching for ChessLink board (max {timeout} secs)...")
            self.init_position = self.cl_brd.position_initialized()
            time.sleep(0.1)

        if self.init_position is True:
            self.log.debug("board position received, init ok.")
        else:
            self.log.error(
                f"no board position received within timeout {timeout}")

    def quit(self):
        self.cl_brd.quit()

    def agent_ready(self):
        return self.init_position

    def get_fen(self):
        return self.cl_brd.position_to_fen(self.cl_brd.position)

    def variant_to_positions(self, _board, moves, plies):
        board = copy.deepcopy(_board)
        pos = []
        mvs = len(moves)
        if mvs > plies:
            mvs = plies

        try:
            pos.append(self.cl_brd.fen_to_position(board.fen()))
            for i in range(mvs):
                board.push(chess.Move.from_uci(moves[i]))
                pos.append(self.cl_brd.fen_to_position(board.fen()))
            for i in range(mvs):
                board.pop()
        except Exception as e:
            self.log.warning(f"Data corruption in variant_to_positions: {e}")
            return None
        return pos

    def color(self, col):
        if col == chess.WHITE:
            col = self.cl_brd.WHITE
        else:
            col = self.cl_brd.BLACK
        return col

    def visualize_variant(self, board, moves, plies=1, freq=-1):
        if freq == -1:
            freq = self.ply_vis_delay
        if plies > 4:
            plies = 4
        pos = self.variant_to_positions(board, moves, plies)
        if pos is not None:
            self.cl_brd.show_deltas(pos, freq)

    def display_info(self, _board, info):
        board = copy.deepcopy(_board)
#        if info['actor'] == self.prefs['computer_player_name']:
        if 'multipv_index' in info:
            if info['multipv_index'] == 1:  # Main variant only
                if 'variant' in info:
                    self.visualize_variant(
                        board, info['variant'], plies=self.max_plies)
        else:
            self.log.error('Unexpected info-format')

    def set_valid_moves(self, board, val):
        if board.turn == chess.WHITE:
            col = self.cl_brd.WHITE
        else:
            col = self.cl_brd.BLACK
        self.cl_brd.move_from(board.fen(), val, col)
