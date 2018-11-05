import logging
import json
import queue
import time
from enum import Enum

import chess
import chess.uci

from chess_link_agent import ChessLinkAgent
from terminal_agent import TerminalAgent
from uci_agent import UciAgent, UciEngines


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
            self.log.warning(
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
        if 'computer_player_name' not in prefs:
            prefs['computer_player_name'] = 'stockfish'
            changed_prefs = True
        if 'computer_player2_name' not in prefs:
            prefs['computer_player2_name'] = ''
            changed_prefs = True
        if 'human_name' not in prefs:
            prefs['human_name'] = 'human'
            changed_prefs = True

        if changed_prefs is True:
            self.write_preferences(prefs)
        return prefs

    def short_fen(self, fen):
        i = fen.find(' ')
        if i == -1:
            self.log.error(
                'Invalid fen position <{}> in short_fen'.format(fen))
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
        self.chess_link_agent = ChessLinkAgent(self.appque)
        self.chess_link_agent.max_plies = self.prefs['max_plies_board']

        self.term_agent = TerminalAgent(self.appque)
        self.term_agent.max_plies = self.prefs['max_plies_terminal']

        self.uci_engines = UciEngines(self.appque)
        self.uci_agent = None
        self.uci_agent2 = None
        avail_engines = ""
        for en in self.uci_engines.engines:
            if len(avail_engines) > 0:
                avail_engines += ', '
            avail_engines += en
        self.log.info(f'Available UCI engines: {avail_engines}')

        if len(self.uci_engines.engines) > 0:
            if self.prefs['computer_player_name'] in self.uci_engines.engines:
                self.uci_agent = UciAgent(
                    self.uci_engines.engines[self.prefs['computer_player_name']])
            else:
                uci_names = list(self.uci_engines.engines.keys())
                self.uci_agent = UciAgent(uci_names[0])
            if self.prefs['computer_player2_name'] in self.uci_engines.engines and self.prefs['computer_player2_name'] != '':
                self.uci_agent2 = UciAgent(
                    self.uci_engines.engines[self.prefs['computer_player2_name']])
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
        if self.term_agent.agent_ready() is True:
            agents += [self.term_agent]
        if self.chess_link_agent.agent_ready() is True:
            agents += [self.chess_link_agent]
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

    def set_mode(self, mode):
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
            self.player_b = self.player_w
            self.player_watch = []
            self.player_watch_name = "None"
        elif mode == self.Mode.PLAYER_ENGINE:
            self.player_w_name = self.prefs['human_name']
            self.player_w = self.get_human_agents()
            self.player_b = self.get_uci_agent()
            if self.player_w == []:
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
        elif mode == self.Mode.ANALYSIS:
            self.log.error("ANALYSIS mode not yet implemented.")
            return False
        elif mode == self.Mode.SETUP:
            self.log.error("SETUP mode not yet implemented.")
            return False
        else:
            self.log.error("Undefined set_mode situation: {}".format(mode))
            return False
        self.mode = mode
        self.update_display_board()
        return True

    class State(Enum):
        IDLE = 0
        BUSY = 1

    def init_board_agents(self):
        if self.chess_link_agent.agent_ready() and self.prefs['import_chesslink_position'] is True:
            self.appque.put(
                {'position_fetch': 'ChessLinkAgent', 'agent': 'prefs'})
            self.state = self.State.BUSY

        ags = ""
        for p in self.player_w + self.player_b:
            if p.agent_ready() is False:
                self.log.error('Failed to initialize agent {}.'.format(p.name))
                exit(-1)
            if len(ags) > 0:
                ags += ", "
            ags += '"'+p.name+'"'
        self.log.info("Agents {} initialized".format(ags))

    def __init__(self):
        self.log = logging.getLogger('mchess')

        self.board = chess.Board()
        self.state = self.State.IDLE
        self.last_info = 0
        self.ponder_move = None

        self.board.reset()

        self.prefs = self.read_preferences()
        self.appque = queue.Queue()

        self.init_agents()
        self.set_default_mode()
        self.init_board_agents()
        self.set_default_mode()

        self.update_display_board()
        self.state_machine_active = True

    def update_display_board(self):
        for agent in self.player_b+self.player_w+self.player_watch:
            dispb = getattr(agent, "display_board", None)
            if callable(dispb):
                attribs = {'unicode': self.prefs['use_unicode_figures'],
                           'white_name': self.player_w_name,
                           'black_name': self.player_b_name
                           }
                agent.display_board(
                    self.board, attribs=attribs)

    def update_display_move(self, msg):
        for agent in self.player_b+self.player_w+self.player_watch:
            dispm = getattr(agent, "display_move", None)
            if callable(dispm):
                agent.display_move(msg)

    def update_display_info(self, msg):
        for agent in self.player_b+self.player_w+self.player_watch:
            dinfo = getattr(agent, "display_info", None)
            if callable(dinfo):
                agent.display_info(
                    self.board, info=msg['curmove'])

    def game_state_machine(self):
        while self.state_machine_active:
            if self.state == self.State.IDLE:
                if self.board.is_game_over() is True:
                    self.log.info('Result: {}'.format(self.board.result()))
                    self.set_mode(self.Mode.NONE)
                    active_player = []
                    passive_player = []

                if self.board.turn == chess.WHITE:
                    active_player = self.player_w
                    passive_player = self.player_b
                else:
                    active_player = self.player_b
                    passive_player = self.player_w

                for agent in passive_player:
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        agent.set_valid_moves(self.board, [])
                    if self.ponder_move != None:
                        setp = getattr(agent, "set_ponder", None)
                        if callable(setp):
                            pass
                            # TODO: agent.set_ponder(self.board, self.ponder_move)

                val = self.valid_moves(self.board)
                for agent in active_player:
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        agent.set_valid_moves(self.board, val)
                    gom = getattr(agent, "go", None)
                    if callable(gom):
                        self.log.debug(
                            'Initiating GO for agent {}'.format(agent.name))
                        agent.go(self.board, self.prefs['think_ms'])
                        break
                self.state = self.State.BUSY

            if self.appque.empty() is False:
                msg = self.appque.get()
                self.appque.task_done()
                self.log.debug("App received msg: {}".format(msg))
                if 'new game' in msg:
                    if self.mode == self.Mode.ENGINE_ENGINE:
                        # TODO: implement
                        self.log.error(
                            'Currently not handling engine-engine new game situation!')
                        continue
                    self.log.info(
                        "New game initiated by {}".format(msg['actor']))
                    self.board.reset()
                    self.update_display_board()
                    self.state = self.State.IDLE

                if 'position_fetch' in msg:
                    for agent in self.player_b+self.player_w:
                        if agent.name == msg['position_fetch']:
                            fen = agent.get_fen()
                            # Only treat as setup, if it's not the start position
                            if self.short_fen(fen) != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                                self.board = chess.Board(fen)
                                self.update_display_board()
                                break
                    self.state = self.State.IDLE

                if 'fen_setup' in msg:
                    self.board = chess.Board(msg['fen'])
                    self.update_display_board()
                    self.state = self.State.IDLE

                if 'move' in msg:
                    self.board.push(chess.Move.from_uci(msg['move']['uci']))
                    self.update_display_move(msg)
                    self.update_display_board()
                    if 'ponder' in msg['move']:
                        self.ponder_move = msg['move']['ponder']
                    self.state = self.State.IDLE

                if 'back' in msg:
                    self.board.pop()
                    self.update_display_board()
                    self.set_mode(self.Mode.PLAYER_PLAYER)
                    self.state = self.State.IDLE

                if 'go' in msg:
                    if self.board.turn == chess.WHITE:
                        self.set_mode(self.Mode.ENGINE_PLAYER)
                    else:
                        self.set_mode(self.Mode.PLAYER_ENGINE)
                    self.state = self.State.IDLE

                if 'curmove' in msg:
                    if time.time()-self.last_info > 1.0:  # throttle
                        self.last_info = time.time()
                        self.update_display_info(msg)

            else:
                time.sleep(0.05)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.INFO)

    mc = Mchess()
    # mc.set_mode(mc.Mode.ENGINE_ENGINE)
    mc.game_state_machine()
