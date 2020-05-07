import argparse
import logging
import sys
import signal
# import threading
import json
import queue
import time
from enum import Enum
import copy
import io

import chess
# import chess.uci
import chess.pgn

ChessLinkAgent = None
TerminalAgent = None
TkAgent = None
WebAgent = None
UciEngines = None
UciAgent = None

def conditional_imports(prefs):
    global ChessLinkAgent, TerminalAgent, TkAgent, WebAgent, UciAgent, UciEngines
    if 'chess_link' in prefs['active_agents']['human']:
        from chess_link_agent import ChessLinkAgent
    if 'terminal' in prefs['active_agents']['human']:
        from terminal_agent import TerminalAgent
    if 'tk' in prefs['active_agents']['human']:
        from tk_agent import TkAgent
    if 'web' in prefs['active_agents']['human']:
        from web_agent import WebAgent
    if len(prefs['active_agents']['computer']) > 0:
        from async_uci_agent import UciAgent, UciEngines

__version__ = "0.2.1"


class Mchess:
    def write_preferences(self, pref):
        try:
            with open("preferences.json", "w") as fp:
                json.dump(pref, fp, indent=4)
        except Exception as e:
            self.log.error(f"Failed to write preferences.json, {e}")

    def read_preferences(self):
        prefs = {}
        changed_prefs = False
        try:
            with open('preferences.json', 'r') as f:
                prefs = json.load(f)
        except Exception as e:
            changed_prefs = True
            self.log.warning(f'Failed to read preferences.json, initializing defaults: {e}')
        if 'think_ms' not in prefs:
            prefs['think_ms'] = 500
            changed_prefs = True
        if 'use_unicode_figures' not in prefs:
            prefs['use_unicode_figures'] = True
            changed_prefs = True
        if 'invert_term_color' not in prefs:
            prefs['invert_term_color'] = False
            changed_prefs = True
        if 'max_plies_terminal' not in prefs:
            prefs['max_plies_terminal'] = 6
            changed_prefs = True
        if 'max_plies_board' not in prefs:
            prefs['max_plies_board'] = 3
            changed_prefs = True
        if 'ply_vis_delay' not in prefs:
            prefs['ply_vis_delay'] = 80
            changed_prefs = True
        if 'import_chesslink_position' not in prefs:
            prefs['import_chesslink_position'] = True
            changed_prefs = True
        if 'computer_player_name' not in prefs:
            prefs['computer_player_name'] = 'stockfish'
            changed_prefs = True
        if 'computer_player2_name' not in prefs:
            prefs['computer_player2_name'] = ''
            changed_prefs = True
        if 'human_name' not in prefs:
            prefs['human_name'] = 'human'
            changed_prefs = True
        if 'active_agents' not in prefs:
            prefs['active_agents'] = {
                "human": ["chess_link", "terminal", "web", "tk"],
                "computer": ["stockfish", "lc0"]
            }
            changed_prefs = True
        if 'log_levels' not in prefs:
            prefs['log_levels'] ={
                'chess.engine': 'ERROR'
            }
            changed_prefs = True
        if changed_prefs is True:
            self.write_preferences(prefs)
        return prefs

    def short_fen(self, fen):
        i = fen.find(' ')
        if i == -1:
            self.log.error(f'Invalid fen position <{fen}> in short_fen')
            return None
        else:
            return fen[:i]

    def valid_moves(self, v_board):
        vals = {}
        for mv in v_board.legal_moves:
            v_board.push(mv)
            vals[self.short_fen(v_board.fen())] = mv.uci()
            v_board.pop()
        return vals

    def init_agents(self):
        self.agents_all = []

        conditional_imports(self.prefs)

        if 'chess_link' in self.prefs['active_agents']['human']:
            self.chess_link_agent = ChessLinkAgent(self.appque, self.prefs)
            self.chess_link_agent.max_plies = self.prefs['max_plies_board']
            self.agents_all += [self.chess_link_agent]
        else:
            self.chess_link_agent = None

        if 'terminal' in self.prefs['active_agents']['human']:
            self.term_agent = TerminalAgent(self.appque, self.prefs)
            self.term_agent.max_plies = self.prefs['max_plies_terminal']
            self.agents_all += [self.term_agent]
        else:
            self.term_agent = None

        if 'tk' in self.prefs['active_agents']['human']:
            self.tk_agent = TkAgent(self.appque, self.prefs)
            self.agents_all += [self.tk_agent]
        else:
            self.tk_agent = None


        if 'web' in self.prefs['active_agents']['human']:
            self.web_agent = WebAgent(self.appque, self.prefs)
            self.agents_all += [self.web_agent]
        else:
            self.web_agent = None

        self.uci_agent = None
        self.uci_agent2 = None
        avail_engines = ""
        if len(self.prefs['active_agents']['computer']) > 0:
            self.uci_engines = UciEngines(self.appque, self.prefs)
            for en in self.uci_engines.engines:
                if len(avail_engines) > 0:
                    avail_engines += ', '
                avail_engines += en
            self.log.info(f'Available UCI engines: {avail_engines}')
            if len(self.uci_engines.engines) > 0:
                if self.prefs['computer_player_name'] in self.uci_engines.engines:
                    self.log.debug(
                        f"{self.prefs['computer_player_name']} | {self.uci_engines.engines[self.prefs['computer_player_name']]['params']} | {self.prefs}")
                    name=self.prefs['computer_player_name']
                    ejs=self.uci_engines.engines[name]['params']
                    self.uci_agent = UciAgent(self.appque, ejs, self.prefs)
                else:
                    uci_names = list(self.uci_engines.engines.keys())
                    ejs=self.uci_engines.engines[uci_names[0]]['params']
                    self.uci_agent = UciAgent(self.appque, ejs, self.prefs)
                self.agents_all += [self.uci_agent]
                if self.prefs['computer_player2_name'] in self.uci_engines.engines and self.prefs['computer_player2_name'] != '':
                    name=self.prefs['computer_player2_name']
                    ejs=self.uci_engines.engines[name]['params']
                    self.uci_agent2 = UciAgent(self.appque, ejs, self.prefs)
                    self.agents_all += [self.uci_agent2]
                else:
                    self.uci_agent2 = None
            else:
                self.uci_agent = None
                self.uci_agent2 = None

    class Mode(Enum):
        NONE = 0
        ANALYSIS = 1
        SETUP = 2
        PLAYER_ENGINE = 3
        ENGINE_PLAYER = 4
        ENGINE_ENGINE = 5
        PLAYER_PLAYER = 6

    def set_default_mode(self):
        if self.uci_agent is not None:
            self.set_mode(self.Mode.PLAYER_ENGINE)
        else:
            self.set_mode(self.Mode.PLAYER_PLAYER)

    def get_human_agents(self):
        agents = []
        if self.term_agent and self.term_agent.agent_ready() is True:
            agents += [self.term_agent]
        if self.chess_link_agent and self.chess_link_agent.agent_ready() is True:
            agents += [self.chess_link_agent]
        if self.tk_agent and self.tk_agent.agent_ready() is True:
            agents += [self.tk_agent]
        if self.web_agent and self.web_agent.agent_ready() is True:
            agents += [self.web_agent]
        return agents

    def get_uci_agent(self):
        agents = []
        if self.uci_agent is not None:
            agents = [self.uci_agent]
        return agents

    def get_uci_agent2(self):
        agents = []
        if self.uci_agent2 is not None:
            agents = [self.uci_agent2]
        return agents

    def uci_stop_engines(self):
        if self.uci_agent is not None and self.uci_agent.busy is True:
            self.uci_agent.stop()
        else:
            self.log.info("not stopping uci")
        if self.uci_agent2 is not None and self.uci_agent2.busy is True:
            self.uci_agent2.stop()
        else:
            self.log.info("not stopping uci2")
        t0 = time.time()
        if self.uci_agent is not None:
            while self.uci_agent.stopping is True:
                time.sleep(0.1)
                if time.time()-t0 > 5:
                    t0=time.time()
                    self.log.warning(f"Problems stopping {self.uci_agent.name}")
        t0=time.time()
        if self.uci_agent2 is not None:
            while self.uci_agent2.stopping is True:
                time.sleep(0.1)
                if time.time()-t0 > 5:
                    t0=time.time()
                    self.log.warning(f"Problems stopping {self.uci_agent.name}")


    def set_mode(self, mode, silent=False):
        if mode == self.Mode.NONE:
            self.player_w = []
            self.player_b = []
            self.player_watch = []
            self.player_watch_name = "None"
            self.player_w_name = "None"
            self.player_b_name = "None"
        elif mode == self.Mode.PLAYER_PLAYER:
            self.player_w_name = self.prefs['human_name']
            self.player_b_name = self.prefs['human_name']
            self.player_w = self.get_human_agents()
            self.player_b = self.get_human_agents()
            self.player_watch = self.get_uci_agent()
            self.player_watch += self.get_uci_agent2()
            if self.player_watch != []:
                self.player_watch_name = ""
                for p in self.player_watch:
                    if len(self.player_watch_name) > 0:
                        self.player_watch_name += ", "
                    self.player_watch_name += p.name
        elif mode == self.Mode.PLAYER_ENGINE:
            self.player_w_name = self.prefs['human_name']
            self.player_w = self.get_human_agents()
            self.player_b = self.get_uci_agent()
            if self.player_b == []:
                self.log.error(
                    "Cannot set PLAYER_ENGINE mode: uci engine 1 not defined.")
                return False
            self.player_b_name = self.player_b[0].name
            self.player_watch = []
            self.player_watch_name = "None"
        elif mode == self.Mode.ENGINE_PLAYER:
            self.player_w = self.get_uci_agent()
            if self.player_w == []:
                self.log.error(
                    "Cannot set ENGINE_PLAYER mode: uci engine 1 not defined.")
                return False
            self.player_w_name = self.player_w[0].name
            self.player_b_name = self.prefs['human_name']
            self.player_b = self.get_human_agents()
            self.player_watch = []
            self.player_watch_name = "None"
        elif mode == self.Mode.ENGINE_ENGINE:
            self.player_w = self.get_uci_agent()
            if self.player_w == []:
                self.log.error(
                    "Cannot set ENGINE_ENGINE mode: uci engine 1 not defined.")
                return False
            self.player_w_name = self.player_w[0].name
            self.player_b = self.get_uci_agent2()
            if self.player_b == []:
                self.log.error(
                    "Cannot set ENGINE_ENGINE mode: uci engine 2 not defined.")
                return False
            self.player_b_name = self.player_b[0].name
            self.player_watch = self.get_human_agents()
            self.player_watch_name = self.prefs['human_name']
        # elif mode == self.Mode.ANALYSIS:
        #     self.log.error("ANALYSIS mode not yet implemented.")
        #     return False
        # elif mode == self.Mode.SETUP:
        #     self.log.error("SETUP mode not yet implemented.")
        #     return False
        else:
            self.log.error(f"Undefined set_mode situation: {mode}")
            return False
        self.mode = mode
        if silent is False:
            self.update_display_board()
        return True

    class State(Enum):
        IDLE = 0
        BUSY = 1

    def import_chesslink_position(self):
        if self.chess_link_agent:
            self.appque.put(
                {'position_fetch': 'ChessLinkAgent', 'actor': self.chess_link_agent.name})
        # self.state = self.State.BUSY  # Check?

    def init_board_agents(self):
        if self.chess_link_agent and self.chess_link_agent.agent_ready() and self.prefs['import_chesslink_position'] is True:
            self.import_chesslink_position()

        ags = ""
        for p in self.agents_all:
            if p.agent_ready() is False:
                self.log.error(f'Failed to initialize agent {p.name}')
            else:
                if len(ags) > 0:
                    ags += ", "
                ags += '"'+p.name+'"'
        self.log.info(f"Agents {ags} initialized")

    def set_loglevels(self, prefs):
        if 'log_levels' in prefs:
            for module in prefs['log_levels']:
                level = logging.getLevelName(prefs['log_levels'][module])
                logi = logging.getLogger(module)
                logi.setLevel(level)

    def __init__(self):
        self.log = logging.getLogger('mchess')

        self.board = chess.Board()
        self.state = self.State.IDLE
        self.last_info = 0
        self.ponder_move = None
        self.analysis_active = False
        self.analysis_buffer_timeout = 3.0

        self.board.reset()
        self.undo_stack = []

        self.prefs = self.read_preferences()
        self.set_loglevels(self.prefs)
        self.appque = queue.Queue()

        self.init_agents()
    
        self.set_default_mode()
        self.init_board_agents()

        # self.update_display_board()
        self.state_machine_active = True

    def stop(self, new_mode=Mode.PLAYER_PLAYER, silent=False):
        self.uci_stop_engines()
        self.log.debug("Stop command.")
        if new_mode is not None:
            self.set_mode(new_mode, silent=silent)
        if silent is False:
            self.update_display_board()
        self.state = self.State.IDLE 

    def is_player_move(self):
        if self.mode == self.Mode.PLAYER_PLAYER:
            return True
        if self.mode == self.Mode.PLAYER_ENGINE and self.board.turn == chess.WHITE:
            return True
        if self.mode == self.Mode.ENGINE_PLAYER and self.board.turn == chess.BLACK:
            return True
        return False

    def update_display_board(self):
        st_board = copy.deepcopy(self.board)
        for agent in self.agents_all:
            dispb = getattr(agent, "display_board", None)
            if callable(dispb):
                attribs = {'unicode': self.prefs['use_unicode_figures'],
                           'invert': self.prefs['invert_term_color'],
                           'white_name': self.player_w_name,
                           'black_name': self.player_b_name
                           }
                agent.display_board(
                   st_board, attribs=attribs)

    def update_display_move(self, mesg):
        for agent in self.agents_all:
            dispm = getattr(agent, "display_move", None)
            if callable(dispm):
                agent.display_move(mesg)

    def update_display_info(self, mesg):
        st_msg = copy.deepcopy(mesg)
        st_board = copy.deepcopy(self.board)
        for agent in self.agents_all:
            dinfo = getattr(agent, "display_info", None)
            if callable(dinfo):
                agent.display_info(
                    st_board, info=st_msg['curmove'])

    def quit(self):
        print("Quitting...")
        # leds off
        if self.chess_link_agent:
            self.chess_link_agent.cl_brd.set_led_off()
        time.sleep(1)
        for agent in self.agents_all:
            fquit = getattr(agent, "quit", None)
            if callable(fquit):
                agent.quit()
        self.state_machine_active = False
        sys.exit(0)

    def quit_signal(self, sig, frame):
        self.quit()

    def game_state_machine(self):
        # mc.set_mode(mc.Mode.ENGINE_ENGINE)
        # signal.signal(signal.SIGINT, mc.quit_signal)
        try:
            self.game_state_machine_NEH()
        except KeyboardInterrupt:
            mc.quit()

    def game_state_machine_NEH(self):
        while self.state_machine_active:
            if self.state == self.State.IDLE and self.appque.empty() is True:
                self.log.info("IDLE")

                if self.board.turn == chess.WHITE:
                    active_player = self.player_w
                    passive_player = self.player_b
                else:
                    active_player = self.player_b
                    passive_player = self.player_w

                self.log.info(f"Active players: {len(active_player)}")
                self.log.info(f"Passive players: {len(passive_player)}")

                for agent in passive_player:
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        agent.set_valid_moves(self.board, [])

                if self.board.is_game_over() is True:
                    self.update_display_board()
                    self.log.info(f'Result: {self.board.result()}')
                    self.set_mode(self.Mode.NONE)

                for agent in passive_player:
                    if self.ponder_move != None:
                        setp = getattr(agent, "set_ponder", None)
                        if callable(setp):
                            pass
                            # agent.set_ponder(self.board, self.ponder_move)

                val = self.valid_moves(self.board)
                for agent in active_player:
                    self.log.info(f"Eval active agent {agent.name}")
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        agent.set_valid_moves(self.board, val)
                    gom = getattr(agent, "go", None)
                    if callable(gom):
                        self.log.debug(f'Initiating GO for agent {agent.name}')
                        brd_copy = copy.deepcopy(self.board)
                        if chess.Move.from_uci('0000') in brd_copy.move_stack:
                            # if history contains NULL moves (UCI: '0000'), do not use
                            # history, or UCI engine will explode.
                            brd_copy.clear_stack()
                            self.board = copy.deepcopy(brd_copy)
                        # print("This is sent to UCI:")
                        # self.term_agent.display_board(brd_copy)
                        self.log.debug(f"Go {agent.name}")
                        agent.go(self.board, self.prefs['think_ms'])
                        self.uci_agent.busy = True
                        self.log.debug(f"Done Go {agent.name}")

                if self.analysis_active:
                    if self.uci_agent is not None:
                        self.uci_agent.busy = True
                        self.uci_agent.go(self.board,mtime=-1, analysis=True)
                    if self.uci_agent2 is not None:
                        self.uci_agent2.busy = True
                        self.uci_agent2.go(self.board,mtime=-1, analysis=True)

                self.state = self.State.BUSY
                self.log.info("BUSY")

            if self.appque.empty() is False:
                # print(self.appque.qsize())
                msg = self.appque.get()
                self.appque.task_done()
                if msg == None:
                    self.log.warning("None message received.")
                    continue
                self.log.debug(f"App received msg: {msg}")

                # remove 'error' element after all transports are updated.
                if 'error' in msg:
                    self.log.error(f"Obsolete protocol. Error condition: {msg['error']}")

                if 'agent-state' in msg:
                    if 'message' not in msg or 'actor' not in msg:
                        self.log.error(f'Invalid <agent-state> message: {msg}')
                    else:
                        if self.uci_agent is not None and msg['actor']==self.uci_agent.name:
                            if msg['agent-state']=='idle':
                                self.uci_agent.busy = False
                        if self.uci_agent2 is not None and msg['actor']==self.uci_agent2.name:
                            if msg['agent-state']=='idle':
                                self.uci_agent2.busy = False
                        for agent in self.agents_all:
                            if agent != msg['actor']:
                                fstate = getattr(agent, "agent_states", None)
                                if callable(fstate):
                                    agent.agent_states(msg)

                if 'new game' in msg:
                    # if self.board.fen() == chess.STARTING_FEN:
                    #     self.log.debug("New game request initiated by {} ignored,
                    #          already at starting position.".format(msg['actor']))
                    #     self.state = self.State.IDLE
                    # else:
                    self.stop(new_mode=None, silent=True)
                    self.log.info(f"New game initiated by {msg['actor']}")
                    self.board.reset()
                    self.undo_stack = []
                    self.update_display_board()
                    self.state = self.State.IDLE
                    if self.analysis_active is True:
                        self.analysis_active = False

                if 'position_fetch' in msg:
                    for agent in self.player_b+self.player_w:
                        if agent.name == msg['position_fetch']:
                            fen = agent.get_fen()
                            # Only treat as setup, if it's not the start position
                            if self.short_fen(fen) != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                                self.log.debug(f"Importing position from {agent.name}, initiated by {msg['actor']}, FEN: {fen}")
                                self.stop(silent=True)
                                if self.analysis_active is True:
                                    self.analysis_active = False
                                self.board = chess.Board(fen)
                                self.update_display_board()
                                self.state = self.State.IDLE
                                break

                if 'fen_setup' in msg:
                    self.stop()
                    if self.analysis_active is True:
                        self.analysis_active = False
                    try:
                        self.board = chess.Board(msg['fen_setup'])
                        self.update_display_board()
                        self.state = self.State.IDLE
                    except Exception as e:
                        if 'fen_setup' not in msg:
                            msg['fen_setup'] = 'None'
                        self.log.warning(f"Invalid FEN {msg['fen_setup']} not imported: {e}")

                if 'pgn_game' in msg:
                    self.stop()
                    if self.analysis_active is True:
                        self.analysis_active = False
                    try:
                        pgnd = msg['pgn_game']['pgn_data']
                        pgndata = io.StringIO(pgnd)
                        game = chess.pgn.read_game(pgndata)
                    except Exception as e:
                        self.log.error(f"Failed to import PGN data {pgnd}: {e}")
                        continue
                    # set metadata
                    try:
                        self.player_w_name = game.headers["White"]
                    except:
                        self.player_w_name = 'unknown'
                    try:
                        self.player_b_name = game.headers["Black"]
                    except:
                        self.player_b_name = 'unknown'
                    self.board = game.board()
                    for move in game.mainline_moves():
                        self.board.push(move)
                    self.update_display_board()
                    self.state = self.State.IDLE

                if 'move' in msg:
                    self.log.info(f"move: {msg['move']['uci']}, {msg}")
                    self.uci_stop_engines()
                    self.undo_stack = []
                    self.board.push(chess.Move.from_uci(msg['move']['uci']))
                    if self.board.is_game_over() is True:
                        msg['move']['result']=self.board.result()
                    else:
                        msg['move']['result']=''
                    self.update_display_move(msg)
                    self.update_display_board()
                    if 'ponder' in msg['move']:
                        self.ponder_move = msg['move']['ponder']
                    self.state = self.State.IDLE

                if 'back' in msg:
                    if len(self.board.move_stack) > 0:
                        self.stop()
                        move = self.board.pop()
                        self.undo_stack.append(move)
                        self.update_display_board()
                        self.state = self.State.IDLE
                    else:
                        self.log.debug(
                            'Cannot take back move, if none has occured.')

                if 'fast-back' in msg:
                    self.stop()
                    while len(self.board.move_stack) > 0:
                        move = self.board.pop()
                        self.undo_stack.append(move)
                    self.update_display_board()
                    self.state = self.State.IDLE

                if 'forward' in msg:
                    if len(self.undo_stack) > 0:
                        self.stop()
                        move = self.undo_stack.pop()
                        self.board.push(move)
                        self.update_display_board()
                        self.state = self.State.IDLE
                    else:
                        self.log.debug(
                            'Cannot move forward, nothing taken back.')
                        # Stack empty, translate to 'go' command.
                        msg['go'] = ''

                if 'fast-forward' in msg:
                    self.stop()
                    while len(self.undo_stack) > 0:
                        move = self.undo_stack.pop()
                        self.board.push(move)
                    self.update_display_board()
                    self.state = self.State.IDLE

                if 'go' in msg:
                    self.stop(new_mode=None)
                    if self.analysis_active is True:
                        self.log.debug("Aborting analysis...")
                        self.analysis_active = False
                    if (self.board.turn == chess.WHITE and self.mode == self.Mode.ENGINE_PLAYER) or (self.board.turn == chess.BLACK and self.mode == self.Mode.PLAYER_ENGINE):
                        pass
                    else:
                        if self.board.turn == chess.WHITE:
                            self.set_mode(self.Mode.ENGINE_PLAYER)
                        else:
                            self.set_mode(self.Mode.PLAYER_ENGINE)
                        self.update_display_board()

                if 'analysis' in msg:
                    self.stop()
                    self.set_mode(self.Mode.PLAYER_PLAYER)
                    self.analysis_active = True
                    if self.uci_agent is not None:
                        self.log.info(f"Starting analysis with {self.uci_agent.name}")
                        # self.uci_agent.busy = True
                        # self.uci_agent.go(self.board,-1, analysis=True)
                    if self.uci_agent2 is not None:
                        self.log.info(f"Starting analysis with {self.uci_agent2.name}")
                        # self.uci_agent2.busy = True
                        # self.uci_agent2.go(self.board, -1, analysis=True)

                if 'turn' in msg:
                    if msg['turn'] == 'white':
                        if self.board.turn != chess.WHITE:
                            self.stop()
                            # self.board.turn=chess.WHITE
                            self.board.push(chess.Move.from_uci('0000'))
                            self.state = self.State.IDLE
                            self.update_display_board()
                            if self.board.turn == chess.WHITE:
                                self.log.info("It's now white's turn.")
                            else:
                                self.log.error(
                                    "TURN information corrupted! (Should be white's turn.)")

                    elif msg['turn'] == 'black':
                        if self.board.turn != chess.BLACK:
                            self.stop()
                            # self.board.turn=chess.BLACK
                            self.board.push(chess.Move.from_uci('0000'))
                            self.state = self.State.IDLE
                            self.update_display_board()
                            if self.board.turn == chess.BLACK:
                                self.log.info("It's now black's turn.")
                            else:
                                self.log.error(
                                    "TURN information corrupted! (Should be black's turn.)")
                    else:
                        self.log.warning(
                            "turn message should send white or black")

                if 'game_mode' in msg:
                    if msg['game_mode'] == 'PLAYER_PLAYER':
                        self.stop(new_mode=self.Mode.PLAYER_PLAYER)
                    elif msg['game_mode'] == 'PLAYER_ENGINE':
                        self.stop(new_mode=self.Mode.PLAYER_ENGINE)
                    elif msg['game_mode'] == 'ENGINE_PLAYER':
                        self.stop(new_mode=self.Mode.ENGINE_PLAYER)
                    elif msg['game_mode'] == 'ENGINE_ENGINE':
                        self.stop(new_mode=self.Mode.ENGINE_ENGINE)

                if 'led_hint' in msg:
                    ply = int(msg['led_hint'])
                    if ply >= 0 and ply < 4:
                        self.prefs['max_plies_board'] = ply
                        self.write_preferences(self.prefs)

                if 'quit' in msg:
                    self.stop()
                    self.quit()

                if 'stop' in msg:
                    # self.analysis_active=False
                    if self.analysis_active is True:
                        self.log.debug("Aborting analysis...")
                        self.analysis_active = False
                    self.stop(silent=False)

                if 'curmove' in msg:
                    self.last_info = time.time()
                    msg['curmove']['appque'] = self.appque.qsize()
                    self.update_display_info(msg)

                if 'turn eboard orientation' in msg:
                    self.stop()
                    if self.chess_link_agent.cl_brd.get_orientation() is False:
                        self.chess_link_agent.cl_brd.set_orientation(True)
                        self.log.info("eboard cable on right side.")
                    else:
                        self.chess_link_agent.cl_brd.set_orientation(False)
                        self.log.info("eboard cable on left side.")
                    self.import_chesslink_position()

                if 'encoding' in msg:
                    self.prefs['use_unicode_figures'] = not self.prefs['use_unicode_figures']
                    self.write_preferences(self.prefs)
                    self.update_display_board()

            else:
                time.sleep(0.05)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='python mchess.py')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='output verbose logging information')
    args = parser.parse_args()

    msg = r"""
 _______                          _                
|__   __|                        (_)               
    | |_   _ _ __ __ _ _   _  ___  _ ___  ___       
    | | | | | '__/ _` | | | |/ _ \| / __|/ _ \      
    | | |_| | | | (_| | |_| | (_) | \__ \  __/      
    |_|\__,_|_|  \__, |\__,_|\___/|_|___/\___|      
                    | |   _____ _         {} 
                    |_|  / ____| |                  
               _ __ ___ | |    | |__   ___  ___ ___ 
              | '_ ` _ \| |    | '_ \ / _ \/ __/ __|
              | | | | | | |____| | | |  __/\__ \__ \\
              |_| |_| |_|\_____|_| |_|\___||___/___/"""
    print(msg.format(__version__))
    print("    Enter 'help' to see an overview of console commands")
    if args.verbose is True:
        log_level = logging.DEBUG
        log_level_e = logging.DEBUG
        log_level_pce = logging.DEBUG
    else:
        log_level = logging.WARNING
        log_level_e = logging.ERROR
        log_level_pce = logging.ERROR

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=log_level)
    logger = logging.getLogger('mchess')
    logger.warning("STARTING")
    logger.setLevel(log_level)
    mc = Mchess()
    mc.game_state_machine()
