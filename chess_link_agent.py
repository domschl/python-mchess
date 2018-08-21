class ChessBoardHelper:
    def __init__(self, appque):
        self.appque = appque
        self.log = logging.getLogger('ChessBoardHelper')
        self.kbd_moves = []
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

    def valid_moves(self, cbrd):
        vals = {}
        for mv in cbrd.legal_moves:
            cbrd.push(mv)
            vals[brd.short_fen(cbrd.fen())] = mv.uci()
            cbrd.pop()
        logging.debug("valid moves: {}".format(vals))
        return vals

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
