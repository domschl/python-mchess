import logging
import chess
import json
import queue
import time
from enum import Enum

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


def short_fen(fen):
    i = fen.find(' ')
    if i == -1:
        logging.error(
            'Invalid fen position <{}> in short_fen'.format(fen))
        return None
    else:
        return fen[:i]


def valid_moves(cbrd):
    vals = {}
    for mv in cbrd.legal_moves:
        cbrd.push(mv)
        vals[short_fen(cbrd.fen())] = mv.uci()
        cbrd.pop()
    return vals


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)

    prefs = {}
    changed_prefs = False
    try:
        with open('preferences.json', 'r') as f:
            prefs = json.load(f)
    except Exception as e:
        changed_prefs = True
        logging.warning(
            'Failed to read preferences.json, initializing defaults: {}'.format(e))

    if 'think_ms' not in prefs:
        prefs['think_ms'] = 500
        changed_prefs = True
    if 'use_unicode_figures' not in prefs:
        prefs['use_unicode_figures'] = True
        changed_prefs = True
    if 'max_plies_terminal' not in prefs:
        prefs['max_plies_terminal'] = 6
        changed_prefs = True
    if 'max_plies_board' not in prefs:
        prefs['max_plies_board'] = 3
        changed_prefs = True
    if 'import_chesslink_position' not in prefs:
        prefs['import_chesslink_position'] = True
        changed_prefs = True

    if changed_prefs is True:
        try:
            with open('preferences.json', 'w') as fw:
                json.dump(prefs, fw)
        except Exception as e:
            logging.error('Failed to save preferences {}'.format(e))

    appque = queue.Queue()

    cla = ChessLinkAgent(appque)
    cla.max_plies = prefs['max_plies_board']
    ta = TerminalAgent(appque)
    ta.max_plies = prefs['max_plies_terminal']
    ua = UciAgent(appque)

    modes = ("analysis", "setup", "player-engine",
             "engine-player", "engine-engine", "player-player")

    class States(Enum):
        IDLE = 0
        BUSY = 1

    # time.sleep(10.0)

    mode = "player-engine"
    player_w = [ta, cla]
    player_b = [ua]
    board = chess.Board()
    state = States.IDLE
    last_info = 0
    ponder_move = None

    if cla.agent_ready() and prefs['import_chesslink_position'] is True:
        appque.put({'position_fetch': 'ChessLinkAgent', 'agent': 'prefs'})
        state = States.BUSY

    ags = ""
    for p in player_w + player_b:
        if p.agent_ready() is False:
            logging.error('Failed to initialize agent {}.'.format(p.name))
            exit(-1)
        if len(ags) > 0:
            ags += ", "
        ags += '"'+p.name+'"'
    logging.info("Agents {} initialized".format(ags))

    while True:
        if state == States.IDLE:
            if mode == 'player-engine':
                if board.turn == chess.WHITE:
                    active_player = player_w
                    passive_player = player_b
                else:
                    active_player = player_b
                    passive_player = player_w
            if mode == 'engine-player':
                if board.turn == chess.BLACK:
                    active_player = player_w
                    passive_player = player_b
                else:
                    active_player = player_b
                    passive_player = player_w
            if mode == 'player-player':
                active_player = player_w
                passive_player = player_w

            for agent in passive_player:
                setm = getattr(agent, "set_valid_moves", None)
                if callable(setm):
                    agent.set_valid_moves(board, [])
                if ponder_move != None:
                    setp = getattr(agent, "set_ponder", None)
                    if callable(setm):
                        agent.set_ponder(board, ponder_move)

            val = valid_moves(board)
            for agent in active_player:
                setm = getattr(agent, "set_valid_moves", None)
                if callable(setm):
                    agent.set_valid_moves(board, val)
                gom = getattr(agent, "go", None)
                if callable(gom):
                    logging.debug(
                        'Initiating GO for agent {}'.format(agent.name))
                    agent.go(board, prefs['think_ms'])
                    break
            state = States.BUSY

        if appque.empty() is False:
            msg = appque.get()
            appque.task_done()
            logging.debug("App received msg: {}".format(msg))
            if 'new game' in msg:
                logging.info(
                    "New game initiated by {}".format(msg['actor']))
                board.reset()
                for agent in player_b+player_w:
                    dispb = getattr(agent, "display_board", None)
                    if callable(dispb):
                        agent.display_board(board)
                state = States.IDLE

            if 'position_fetch' in msg:
                for agent in player_b+player_w:
                    if agent.name == msg['position_fetch']:
                        fen = agent.get_fen()
                        # Only treat as setup, if it's not the start position
                        if short_fen(fen) != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                            board = chess.Board(fen)
                            for agent2 in player_b+player_w:
                                dispb = getattr(agent2, "display_board", None)
                                if callable(dispb):
                                    agent2.display_board(board)
                            break
                state = States.IDLE

            if 'fen_setup' in msg:
                board = chess.Board(msg['fen'])
                for agent in player_b+player_w:
                    dispb = getattr(agent, "display_board", None)
                    if callable(dispb):
                        agent.display_board(board)
                state = States.IDLE

            if 'move' in msg:
                board.push(chess.Move.from_uci(msg['move']['uci']))
                for agent in player_b+player_w:
                    dispm = getattr(agent, "display_move", None)
                    if callable(dispm):
                        agent.display_move(msg)
                    dispb = getattr(agent, "display_board", None)
                    if callable(dispb):
                        agent.display_board(board)
                if 'ponder' in msg['move']:
                    ponder_move = msg['move']['ponder']
                state = States.IDLE

            if 'back' in msg:
                board.pop()
                for agent in player_b+player_w:
                    disp = getattr(agent, "display_board", None)
                    if callable(disp):
                        agent.display_board(board)
                mode = 'player-player'
                state = States.IDLE

            if 'go' in msg:
                if board.turn == chess.WHITE:
                    mode = 'engine-player'
                else:
                    mode = 'player-engine'
                state = States.IDLE

            if 'curmove' in msg:
                if time.time()-last_info > 1.0:  # throttle
                    last_info = time.time()
                    uci = msg['curmove']['variant']
                    for agent in player_b+player_w:
                        dinfo = getattr(agent, "display_info", None)
                        if callable(dinfo):
                            agent.display_info(
                                board, info=msg['curmove'])

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
