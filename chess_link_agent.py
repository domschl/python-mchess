import logging
import queue
import time

import chess
import chess_link as cl


class ChessLinkAgent:
    def __init__(self, appque):
        self.appque = appque
        self.log = logging.getLogger('ChessLinkAgent')
        self.cl_brd = cl.ChessLink(appque)

        self.cl_brd.get_version()
        time.sleep(0.1)
        self.cl_brd.set_debounce(4)
        time.sleep(0.1)
        self.cl_brd.get_scan_time_ms()
        time.sleep(0.1)
        self.cl_brd.set_scan_time_ms(100.0)
        time.sleep(0.1)
        self.cl_brd.get_scan_time_ms()
        time.sleep(0.1)
        self.init_position = True
        self.cl_brd.get_position()

    def variant_to_positions(self, cbrd, variant, plys):
        pos = []
        mvs = len(variant)
        if mvs > plys:
            mvs = plys

        pos.append(self.cl_brd.fen_to_position(cbrd.fen()))
        for i in range(mvs):
            cbrd.push(chess.Move.from_uci(variant[i]))
            pos.append(self.cl_brd.fen_to_position(cbrd.fen()))
        for i in range(mvs):
            cbrd.pop()
        return pos

    def color(self, col):
        if col == chess.WHITE:
            col = self.cl_brd.WHITE
        else:
            col = self.cl_brd.BLACK
        return col

    def visualize_variant(self, cbrd, variant, plys=1, freq=80):
        if plys > 4:
            plys = 4
        pos = self.variant_to_positions(cbrd, variant, plys)
        self.cl_brd.show_deltas(pos, freq)

    def set_valid_moves(self, board, val):
        if board.turn == chess.WHITE:
            col = self.cl_brd.WHITE
        else:
            col = self.cl_brd.BLACK
        self.cl_brd.move_from(board.fen(), val, col)
