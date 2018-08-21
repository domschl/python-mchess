import chess
import chess_link as cl


class ChessLinkAgent:
    def __init__(self, appque):
        self.appque = appque
        self.log = logging.getLogger('ChessLinkAgent')
        self.brd = cl.ChessLink(appque)

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
