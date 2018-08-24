import logging
import chess
import json
import queue
import time

import chess
import chess.uci

from chess_link_agent import ChessLinkAgent
from terminal_agent import TerminalAgent
from uci_agent import UciAgent


def write_preferences(prefs):
    try:
        with open("preferences.json", "w") as f:
            json.dump(prefs, f)
    except Exception as e:
        logging.error("Failed to write preferences.json, {}".format(e))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)

    appque = queue.Queue()

    cla = ChessLinkAgent(appque)
    ta = TerminalAgent(appque)
    ua = UciAgent(appque)

    modes = ("analysis", "setup", "player-engine",
             "engine-player", "engine-engine", "player-player")

    mode = "player-engine"
    board = chess.Board()

    while True:
        if appque.empty() is False:
            msg = appque.get()
            appque.task_done()
            logging.debug("App received msg: {}".format(msg))

        else:
            time.sleep(0.05)


"""
    try:
        with open("preferences.json", "r") as f:
            prefs = json.load(f)
    except:
        prefs = {
            'think_ms': 3000,
            'use_unicode_figures': True,
            'max_ply': 6
        }
        write_preferences(prefs)

    if 'max_ply' not in prefs:
        prefs['max_ply'] = 8
        write_preferences(prefs)

    bhlp = ChessBoardHelper(appque)

    bhlp.load_engines()
    logging.debug('{} engines loaded.'.format(len(bhlp.engines)))
    if len(bhlp.engines) == 0:
        logging.error("No engine defined! Check uci_engines.json.")
        exit(-1)

    engine_no = 0
    if 'default-engine' in bhlp.engines:
        engine_no = bhlp.engines['default-engine']
        if engine_no > len(bhlp.engines['engines']):
            engine_no = 0
    engine = chess.uci.popen_engine(bhlp.engines['engines'][engine_no]['path'])
    logging.info('Loading engine {}.'.format(
        bhlp.engines['engines'][engine_no]['name']))
    engine.uci()
    # options
    engine.isready()
    bhlp.uci_handler(engine)

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
        last_variant = time.time()
        score = ''
        nps = 0
        depth = 0
        seldepth = 0

        bhlp.keyboard_handler()

        while True:
            if appque.empty() is False:
                msg = appque.get()
                appque.task_done()
                logging.debug("App received msg: {}".format(msg))
                if 'error' in msg:
                    logging.error(msg['error'])
                    print()
                    exit(-1)
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
                    last_variant = time.time()
                    if ana_mode == True and msg['move']['actor'] == 'uci-engine':
                        engine.position(cbrd)
                        engine.go(infinite=True, async_callback=True)
                        continue
                    uci = msg['move']['uci']
                    print()
                    logging.debug("{} move: {}".format(
                        msg['move']['actor'], uci))
                    ft = engine.stop(async_callback=True)
                    ft.result()
                    time.sleep(0.2)
                    mv = chess.Move.from_uci(uci)
                    cbrd.push(mv)
                    ams = bhlp.ascii_move_stack(
                        cbrd, score, use_unicode_chess_figures=prefs['use_unicode_figures'])
                    brd.print_position_ascii(brd.fen_to_position(
                        cbrd.fen()), bhlp.color(brd, cbrd.turn), use_unicode_chess_figures=prefs['use_unicode_figures'], move_stack=ams)
                    score = ''
                    nps = 0
                    seldepth = 0
                    depth = 0
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
                                valm = ""
                                for v in vals:
                                    valm += '{} '.format(vals[v])
                                logging.debug('{} {}'.format(valm, brd.turn))
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
                    if time.time()-last_variant > 1.0:  # throttle
                        last_variant = time.time()
                        uci = msg['curmove']['variant']
                        logging.debug("{} variant: {}".format(
                            msg['curmove']['actor'], msg['curmove']['variant string']))
                        bhlp.visualize_variant(
                            brd, cbrd, msg['curmove']['variant'], hint_ply, 50)
                        lvar = len(uci)
                        if lvar > prefs['max_ply']:
                            lvar = prefs['max_ply']
                        status = '[eval: {} nps: {} depth: {}/{}] '.format(
                            score, nps, depth, seldepth)
                        for i in range(lvar):
                            status += uci[i] + " "
                        print(status, end='\r')
                if 'score' in msg:
                    if msg['score']['mate'] is not None:
                        logging.debug('Mate in {}'.format(
                            msg['score']['mate']))
                        score = '#{}'.format(msg['score']['mate'])
                    else:
                        logging.debug('Score {}'.format(msg['score']['cp']))
                        score = '{}'.format(float(msg['score']['cp'])/100.0)
                if 'depth' in msg:
                    depth = msg['depth']
                if 'seldepth' in msg:
                    seldepth = msg['seldepth']
                if 'nps' in msg:
                    nps = msg['nps']
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
                        logging.debug(
                            'Engine move time is {} ms'.format(prefs['think_ms']))
                        write_preferences(prefs)
                if 'hint' in msg:
                    if 'ply' in msg:
                        hint_ply = msg['ply']
                if 'max_ply' in msg:
                    prefs['max_ply'] = msg['max_ply']
                if 'write' in msg:
                    write_preferences(prefs)
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
                time.sleep(0.1)
"""
