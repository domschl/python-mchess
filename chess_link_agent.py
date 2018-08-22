import logging
import queue
import chess
import chess_link as cl


class ChessLinkAgent:
    def __init__(self, appque):
        self.appque = appque
        self.log = logging.getLogger('ChessLinkAgent')
        self.cl_brd = cl.ChessLink(appque)

    def valid_moves(self, cbrd):
        vals = {}
        for mv in cbrd.legal_moves:
            cbrd.push(mv)
            vals[self.cl_brd.short_fen(cbrd.fen())] = mv.uci()
            cbrd.pop()
        logging.debug("valid moves: {}".format(vals))
        return vals

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
