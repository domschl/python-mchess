''' MChess Turquoise application '''
import logging
import sys
import time
from enum import Enum
import copy
import io

import chess
import chess.pgn

class TurquoiseDispatcher:
    ''' Main dispatcher and event state machine '''
    def __init__(self, appque, prefs, agents, uci_conf):
        self.log = logging.getLogger('StateMachine')
        self.appque = appque
        self.prefs = prefs
        self.agents = agents
        self.uci_engine_configurator = uci_conf

        # XXX: to be removed:
        self.chesslink_agent = None
        self.term_agent = None
        self.tk_agent = None
        self.qt_agent = None
        self.web_agent = None
        self.uci_agent = None
        self.uci_agent2 = None

        self.board = chess.Board()
        self.state = self.State.IDLE

        self.last_info = 0
        self.ponder_move = None
        self.analysis_active = False
        self.analysis_buffer_timeout = 3.0

        self.player_w = None
        self.player_b = None
        self.player_watch = None
        self.player_w_name = None
        self.player_b_name = None
        self.player_watch_name = None

        self.board.reset()
        self.undo_stack = []
        self.undo_stats_stack = []
        self.stats = []

        self.mode = None

        self.init_agents()

        self.set_default_mode()
        self.init_board_agents()

        # self.update_display_board()
        self.state_machine_active = True

        self.cmds={
            'quit': self.quit,
            'agent_state': self.agent_state,
            'new_game': self.new_game,
            'position_fetch': self.position_fetch,
            'import_fen': self.import_fen,
            'import_pgn': self.import_pgn,
            'move': self.move,
            'move_back': self.move_back,
            'move_forward': self.move_forward,
            'move_start': self.move_start,
            'move_end': self.move_end,
            'go': self.go,
            'analyse': self.analyse,
            'turn': self.turn,
            'game_mode': self.game_mode,
            'led_info': self.led_info,
            'stop': self.stop_cmd,
            'current_move_info': self.current_move_info,
            'text_encoding': self.text_encoding,
            'turn_hardware_board': self.turn_hardware_board,
            'raw_board_position': self.raw_board_position,
            'engine_list': self.engine_list
        }

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
        # XXX temp. Gurkenschnorchel
        self.agents_all = []
        if 'chesslink' in self.agents:
            self.chesslink_agent = self.agents['chesslink']
            self.agents_all.append(self.chesslink_agent)
            # XXX: self.chesslink_agent.max_plies = self.prefs['chesslink']['max_plies_board']
        else:
            self.chesslink_agent = None
        if 'terminal' in self.agents:
            self.term_agent = self.agents['terminal']
            self.agents_all.append(self.term_agent)
            # XXX: self.term_agent.max_plies = self.prefs['max_plies_terminal']
        else:
            self.term_agent = None
        if 'tk' in self.agents:
            self.tk_agent = self.agents['tk']
            self.agents_all.append(self.tk_agent)
        else:
            self.tk_agent = None
        if 'qt' in self.agents:
            self.qt_agent = self.agents['qt']
            self.agents_all.append(self.qt_agent)
        else:
            self.qt_agent = None
        if 'web' in self.agents:
            self.web_agent = self.agents['web']
            self.agents_all.append(self.web_agent)
        else:
            self.qt_agent = None

        self.uci_agent = None
        self.uci_agent2 = None
        if 'uci1' in self.agents:
            self.uci_agent = self.agents['uci1']
            self.agents_all.append(self.uci_agent)
        if 'uci2' in self.agents:
            self.uci_agent2 = self.agents['uci2']
            self.agents_all.append(self.uci_agent2)

        self.uci_engine_configurator.publish_uci_engines()
        
    class Mode(Enum):
        ''' state machine play mode '''
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
        if self.chesslink_agent and self.chesslink_agent.agent_ready() is True:
            agents += [self.chesslink_agent]
        if self.tk_agent and self.tk_agent.agent_ready() is True:
            agents += [self.tk_agent]
        if self.qt_agent and self.qt_agent.agent_ready() is True:
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
            self.log.debug("not stopping uci")
        if self.uci_agent2 is not None and self.uci_agent2.busy is True:
            self.uci_agent2.stop()
        else:
            self.log.debug("not stopping uci2")
        t0 = time.time()
        if self.uci_agent is not None:
            while self.uci_agent.stopping is True:
                time.sleep(0.1)
                if time.time()-t0 > 5:
                    t0 = time.time()
                    self.log.warning(f"Problems stopping {self.uci_agent.name}")
        t0 = time.time()
        if self.uci_agent2 is not None:
            while self.uci_agent2.stopping is True:
                time.sleep(0.1)
                if time.time()-t0 > 5:
                    t0 = time.time()
                    self.log.warning(f"Problems stopping {self.uci_agent2.name}")


    def set_mode(self, mode, silent=False):
        if mode == self.Mode.NONE:
            self.player_w = []
            self.player_b = []
            self.player_watch = []
            self.player_watch_name = "None"
            self.player_w_name = "None"
            self.player_b_name = "None"
        elif mode == self.Mode.PLAYER_PLAYER:
            self.player_w_name = self.prefs['default_human_player']['name']
            self.player_b_name = self.prefs['default_human_player']['name']
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
            self.player_w_name = self.prefs['default_human_player']['name']
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
            self.player_b_name = self.prefs['default_human_player']['name']
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
            self.player_watch_name = self.prefs['default_human_player']['name']
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
            self.update_stats()
        return True

    class State(Enum):
        ''' State machine states '''
        IDLE = 0
        BUSY = 1

    def import_chesslink_position(self):
        if self.chesslink_agent:
            self.appque.put(
                {'cmd': 'position_fetch', 'from': 'ChessLinkAgent', 'actor': 'dispatcher'})
        # self.state = self.State.BUSY  # Check?

    def init_board_agents(self):
        if self.chesslink_agent and self.chesslink_agent.agent_ready() and \
           self.prefs['chesslink']['import_position'] is True:
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
                attribs = {'white_name': self.player_w_name,
                           'black_name': self.player_b_name
                           }
                agent.display_board(st_board, attribs=attribs)

    def update_display_move(self, mesg):
        for agent in self.agents_all:
            dispm = getattr(agent, "display_move", None)
            if callable(dispm):
                agent.display_move(mesg)

    def update_engine_list(self, mesg):
        for agent in self.agents_all:
            dispm = getattr(agent, "engine_list", None)
            if callable(dispm):
                agent.engine_list(mesg)

    def update_stats(self):
        for agent in self.agents_all:
            dispm = getattr(agent, "game_stats", None)
            if callable(dispm):
                agent.game_stats(self.stats)

    def update_display_info(self, mesg, max_board_preview_hmoves=6):
        st_msg = copy.deepcopy(mesg)
        st_board = copy.deepcopy(self.board)
        # XXX: deepcopy needs cleanup
        ninfo = copy.deepcopy(mesg)
        nboard = copy.deepcopy(self.board)
        nboard_cut = copy.deepcopy(nboard)
        max_cut = max_board_preview_hmoves
        if 'variant' in ninfo and 'san_variant' not in ninfo:
            ml = []
            mv = ''
            if nboard.turn is False:
                mv = (nboard.fullmove_number,)
                mv += ("..",)
            rel_mv = 0
            for move in ninfo['variant']:
                if move is None:
                    self.log.error("None-move in variant: {}".format(ninfo))
                if nboard.turn is True:
                    mv = (nboard.fullmove_number,)
                try:
                    san = nboard.san(chess.Move.from_uci(move))
                except Exception as e:
                    self.log.warning(
                        "Internal error '{}' at san conversion.".format(e))
                    san = None
                if san is not None:
                    mv += (san,)
                else:
                    self.log.info(
                        "Variant cut off due to san-conversion-error: '{}'".format(mv))
                    break
                if nboard.turn is False:
                    ml.append(mv)
                    mv = ""
                nboard.push(chess.Move.from_uci(move))
                if rel_mv < max_cut:
                    nboard_cut.push(chess.Move.from_uci(move)) 
                    rel_mv += 1
            if mv != "":
                ml.append(mv)
                mv = ""
            st_msg['san_variant'] = ml
            st_msg['preview_fen'] = nboard_cut.fen()

        for agent in self.agents_all:
            dinfo = getattr(agent, "display_info", None)
            if callable(dinfo):
                agent.display_info(
                    st_board, info=st_msg)

    def quit_signal(self, sig, frame):
        self.log.debug(f"sig: {sig} frame: {frame}")
        self.quit()

    def game_state_machine(self):
        # mc.set_mode(mc.Mode.ENGINE_ENGINE)
        # signal.signal(signal.SIGINT, mc.quit_signal)
        try:
            self.game_state_machine_NEH()
        except KeyboardInterrupt:
            self.quit()

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
                    self.log.info(f"Checking {agent.name} for set_valid_moves")
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        self.log.info(f"Resetting {agent.name} valid-move list")
                        agent.set_valid_moves(self.board, [])

                if self.board.is_game_over() is True:
                    self.update_display_board()
                    self.log.info(f'Result: {self.board.result()}')
                    self.set_mode(self.Mode.NONE)

                for agent in passive_player:
                    if self.ponder_move is not None:
                        setp = getattr(agent, "set_ponder", None)
                        if callable(setp):
                            pass
                            # agent.set_ponder(self.board, self.ponder_move)

                val = self.valid_moves(self.board)
                for agent in active_player:
                    self.log.info(f"Eval active agent {agent.name}")
                    setm = getattr(agent, "set_valid_moves", None)
                    if callable(setm):
                        self.log.info(f"Sending {agent.name} valid_moves")
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
                        agent.go(self.board, self.prefs['computer']['think_ms'])
                        self.uci_agent.busy = True
                        self.log.debug(f"Done Go {agent.name}")

                if self.analysis_active:
                    if self.uci_agent is not None:
                        self.uci_agent.busy = True
                        self.log.info("Start uci_agent")
                        self.uci_agent.go(self.board, mtime=-1, analysis=True)
                    if self.uci_agent2 is not None:
                        self.uci_agent2.busy = True
                        self.log.info("Start uci_agent2")
                        self.uci_agent2.go(self.board, mtime=-1, analysis=True)

                self.state = self.State.BUSY
                self.log.info("BUSY")

            if self.appque.empty() is False:
                # print(self.appque.qsize())
                msg = self.appque.get()
                self.appque.task_done()
                if msg is None:
                    self.log.warning("None message received.")
                    continue
                self.log.debug(f"App received msg: {msg}")
                if 'cmd' not in msg:
                    if 'actor' in msg:
                        agent=msg['actor']
                    else:
                        agent='unknown'
                    self.log.error(f"Old-style message {msg} received from {agent}, ignored, please update agent!")
                    continue
                if msg['cmd'] in self.cmds:
                    self.cmds[msg['cmd']](msg)
                else:
                    if 'actor' in msg:
                        agent=msg['actor']
                    else:
                        agent='unknown'
                    self.log.error(f"Message cmd {msg['cmd']} has not yet been implemented (from: {agent}), msg: {msg}")
                    continue
            else:
                time.sleep(0.05)
    
    def agent_state(self, msg):
        if 'message' not in msg or 'actor' not in msg:
            self.log.error(f'Invalid <agent_state> message: {msg}')
        else:
            if self.uci_agent is not None and msg['actor'] == self.uci_agent.name:
                if msg['state'] == 'idle':
                    self.uci_agent.busy = False
            if self.uci_agent2 is not None and msg['actor'] == self.uci_agent2.name:
                if msg['state'] == 'idle':
                    self.uci_agent2.busy = False
            for agent in self.agents_all:
                if agent != msg['actor']:
                    fstate = getattr(agent, "agent_states", None)
                    if callable(fstate):
                        agent.agent_states(msg)

    def quit(self):
        print("Quitting...")
        self.stop()
        # leds off
        if self.chesslink_agent:
            self.chesslink_agent.cl_brd.set_led_off()
        time.sleep(1)
        for agent in self.agents_all:
            fquit = getattr(agent, "quit", None)
            if callable(fquit):
                agent.quit()
        self.state_machine_active = False
        sys.exit(0)

    def new_game(self, msg):
        self.stop(new_mode=None, silent=True)
        self.log.info(f"New game initiated by {msg['actor']}")
        self.board.reset()
        self.undo_stack = []
        self.undo_stats_stack = []
        self.stats = []
        self.update_stats()
        self.update_display_board()
        self.state = self.State.IDLE
        if self.analysis_active is True:
            self.analysis_active = False

    def position_fetch(self, msg):
        for agent in self.player_b+self.player_w:
            if agent.name == msg['from']:
                fen = agent.get_fen()
                # Only treat as setup, if it's not the start position
                if self.short_fen(fen) != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR":
                    self.log.debug(f"Importing position from {agent.name}, by" \
                                    " {msg['actor']}, FEN: {fen}")
                    self.stop(silent=True)
                    self.stats = []
                    self.undo_stack = []
                    self.undo_stats_stack = []
                    if self.analysis_active is True:
                        self.analysis_active = False
                    self.board = chess.Board(fen)
                    self.update_display_board()
                    self.update_stats()
                    self.state = self.State.IDLE
                    break

    def import_fen(self, msg):
        self.stop()
        self.stats = []
        self.undo_stack = []
        self.undo_stats_stack = []
        if self.analysis_active is True:
            self.analysis_active = False
        try:
            self.board = chess.Board(msg['fen'])
            self.log.info(f"Imported FEN: {msg['fen']}")
            self.update_display_board()
            self.state = self.State.IDLE
        except Exception as e:
            self.log.warning(f"Invalid import FEN {msg} not imported: {e}")
        self.update_stats()

    def import_pgn(self, msg):
        self.stop()
        self.stats = []
        self.undo_stack = []
        self.undo_stats_stack = []
        if self.analysis_active is True:
            self.analysis_active = False
        try:
            pgnd = msg['pgn']
            pgndata = io.StringIO(pgnd)
            game = chess.pgn.read_game(pgndata)
        except Exception as e:
            self.log.error(f"Failed to import PGN data {pgnd}: {e}")
            return
        # set metadata
        try:
            self.player_w_name = game.headers["White"]
        except Exception as e:
            self.log.warning(f'PGN misses White-name-field: {e}')
            self.player_w_name = 'unknown'
        try:
            self.player_b_name = game.headers["Black"]
        except Exception as e:
            self.log.warning(f'PGN misses Black-name-field: {e}')
            self.player_b_name = 'unknown'
        self.board = game.board()
        for move in game.mainline_moves():
            self.board.push(move)
        self.update_display_board()
        self.update_stats()
        self.state = self.State.IDLE

    def move(self, msg):
        self.log.info(f"move: {msg['uci']}, {msg}")
        self.log.info(f"board.fen()")
        self.uci_stop_engines()
        self.undo_stack = []
        self.undo_stats_stack = []

        stat={}
        if 'score' in msg:
            stat['score'] = msg['score']
        if 'depth' in msg:
            stat['depth'] = msg['depth']
        if 'seldepth' in msg:
            stat['seldepth'] = msg['seldepth']
        if 'nps' in msg:
            stat['nps'] = msg['nps']
        if 'tbhits' in msg:
            stat['tbhits'] = msg['tbhits']
        stat['move_number'] = self.board.fullmove_number
        if self.board.turn == chess.WHITE:
            stat['color'] = 'WHITE'
            stat['halfmove_number'] = self.board.fullmove_number * 2
            stat['player'] = self.player_w_name
        else:
            stat['color'] = 'BLACK'
            stat['halfmove_number'] = self.board.fullmove_number * 2 + 1
            stat['player'] = self.player_b_name
        self.stats.append(stat)
        self.update_stats()
        
        self.board.push(chess.Move.from_uci(msg['uci']))
        if self.board.is_game_over() is True:
            msg['result'] = self.board.result()
        else:
            msg['result'] = ''
        
        self.update_display_move(msg)
        self.update_display_board()
        if 'ponder' in msg:
            self.ponder_move = msg['ponder']
        self.state = self.State.IDLE

    def move_back(self, msg):
        if len(self.board.move_stack) > 0:
            self.stop()
            move = self.board.pop()
            self.undo_stack.append(move)
            self.undo_stats_stack.append(self.stats.pop())
            self.update_display_board()
            self.update_stats();
            self.state = self.State.IDLE
        else:
            self.log.debug(
                'Cannot take back move, if none has occured.')

    def move_start(self, msg):
        self.stop()
        while len(self.board.move_stack) > 0:
            move = self.board.pop()
            self.undo_stack.append(move)
            self.undo_stats_stack.append(self.stats.pop())
        self.update_display_board()
        self.update_stats();
        self.state = self.State.IDLE

    def move_forward(self, msg):
        if len(self.undo_stack) > 0:
            self.stop()
            move = self.undo_stack.pop()
            self.stats.append(self.undo_stats_stack.pop())
            self.board.push(move)
            self.update_display_board()
            self.update_stats();
            self.state = self.State.IDLE
        else:
            self.log.debug(
                'Cannot move forward, nothing taken back.')
            # Stack empty, translate to 'go' command.
            msg['cmd']='go'
            self.go(msg)

    def move_end(self, msg):
        self.stop()
        while len(self.undo_stack) > 0:
            move = self.undo_stack.pop()
            self.board.push(move)
            self.stats.append(self.undo_stats_stack.pop())
        self.update_display_board()
        self.update_stats();
        self.state = self.State.IDLE

    def go(self, msg):
        self.stop(new_mode=None)
        if self.analysis_active is True:
            self.log.debug("Aborting analysis...")
            self.analysis_active = False
        if (self.board.turn == chess.WHITE and self.mode == self.Mode.ENGINE_PLAYER) or\
            (self.board.turn == chess.BLACK and self.mode == self.Mode.PLAYER_ENGINE):
            pass
        else:
            if self.board.turn == chess.WHITE:
                self.set_mode(self.Mode.ENGINE_PLAYER)
            else:
                self.set_mode(self.Mode.PLAYER_ENGINE)
            self.update_display_board()

    def analyse(self, msg):
        self.stop()
        self.set_mode(self.Mode.PLAYER_PLAYER)
        self.analysis_active = True
        if self.uci_agent is not None:
            self.log.info(f"Starting analysis with {self.uci_agent.name}")
        if self.uci_agent2 is not None:
            self.log.info(f"Starting analysis with {self.uci_agent2.name}")

    def turn(self, msg):
        if msg['color'] == 'white':
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

        elif msg['color'] == 'black':
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
                "turn message should send 'color' white or black")

    def game_mode(self, msg):
        if msg['mode'] == 'human-human':
            self.stop(new_mode=self.Mode.PLAYER_PLAYER)
        elif msg['mode'] == 'human-computer':
            self.stop(new_mode=self.Mode.PLAYER_ENGINE)
        elif msg['mode'] == 'computer-human':
            self.stop(new_mode=self.Mode.ENGINE_PLAYER)
        elif msg['mode'] == 'computer-computer':
            self.stop(new_mode=self.Mode.ENGINE_ENGINE)
        else:
            self.log.error(f"Undefined game_mode {msg['mode']} in {msg}")

    def led_info(self, msg):
        ply = int(msg['plies'])
        if ply >= 0 and ply < 4:
            self.prefs['chesslink']['max_plies_board'] = ply
            # XXX updates prefs: self.write_preferences(self.prefs)

    def stop_cmd(self, msg):
        # self.analysis_active=False
        if self.analysis_active is True:
            self.log.debug("Aborting analysis...")
            self.analysis_active = False
        self.stop(silent=False)

    def current_move_info(self, msg):
        self.last_info = time.time()
        msg['appque'] = self.appque.qsize()
        self.update_display_info(msg)

    def turn_hardware_board(self, msg):
        self.stop()
        if self.chesslink_agent.cl_brd.get_orientation() is False:
            self.chesslink_agent.cl_brd.set_orientation(True)
            self.log.info("eboard cable on right side.")
        else:
            self.chesslink_agent.cl_brd.set_orientation(False)
            self.log.info("eboard cable on left side.")
        self.import_chesslink_position()

    def text_encoding(self, msg):
        self.prefs['terminal']['use_unicode_figures'] = msg['unicode'] # not self.prefs['terminal']['use_unicode_figures']
        # XXX: update prefs: self.write_preferences(self.prefs)
        # XXX: old implementation toggles and doesn't save?! See terminal, commented out.
        self.update_display_board()

    def raw_board_position(self, msg):
        self.log.debug(f"Raw board position (unchecked) on Hardware board: {msg['fen']}")

    def engine_list(self, msg):
        self.update_engine_list(msg)