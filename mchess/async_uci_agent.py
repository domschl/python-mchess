''' Chess UCI Engine agent using python-chess's async interface '''
import logging
import time
import queue
import json
import os
import threading
import copy
from distutils.spawn import find_executable
import glob

import asyncio
import chess
import chess.engine


class UciEngines:
    """Search for UCI engines and make a list of all available engines
    """
    ENGINE_JSON_VERSION = 1

    def __init__(self, appque, prefs):
        self.log = logging.getLogger("UciEngines")
        self.prefs = prefs
        self.appque = appque
        self.name = "UciEngines"

        COMMON_ENGINES = ['stockfish', 'crafty', 'komodo']
        for engine_name in COMMON_ENGINES:
            engine_json_path = os.path.join('engines', engine_name+'.json')
            if os.path.exists(engine_json_path):
                inv = False
                try:
                    with open(engine_json_path) as f:
                        engine_json = json.load(f)
                    if 'version' in engine_json and \
                       engine_json['version'] == self.ENGINE_JSON_VERSION:
                        inv = False
                    else:
                        self.log.warning(
                            f"Wrong version information in {engine_json_path}")
                        inv = True
                except Exception as e:
                    self.log.error(
                        f"Json engine load of {engine_json_path} failed: {e}")
                    inv = True
                if inv is False:
                    continue
            engine_path = find_executable(engine_name)
            if engine_path is not None:
                engine_json = {'name': engine_name,
                               'path': engine_path,
                               'active': True,
                               'version': self.ENGINE_JSON_VERSION}
                with open(engine_json_path, 'w') as f:
                    try:
                        json.dump(engine_json, f, indent=4)
                    except Exception as e:
                        self.log.error(
                            f'Failed to write no engine description {engine_json_path}: {e}')
                        continue
                self.log.info(f'Found new/updated UCI engine {engine_name}')
        self.engine_json_list = glob.glob('engines/*.json')
        if len(self.engine_json_list) == 0:
            self.log.warning(
                'No UCI engines found, and none is defined in engines subdir.')
        self.engines = {}
        for engine_json_path in self.engine_json_list:
            if '-template' in engine_json_path or '-help' in engine_json_path:
                continue
            try:
                with open(engine_json_path, 'r') as f:
                    engine_json = json.load(f)
            except Exception as e:
                self.log.error(
                    f'Failed to read UCI engine description {engine_json_path}: {e}')
                continue
            if 'name' not in engine_json:
                self.log.error(f"Mandatory parameter 'name' is not in UCI description "
                               "{engine_json_path}, ignoring this engine.")
                continue
            if 'path' not in engine_json:
                self.log.error(f"Mandatory parameter 'path' is not in UCI description "
                               "{engine_json_path}, ignoring this engine.")
                continue
            if os.path.exists(engine_json['path']) is False:
                self.log.error(f"Invalid path {engine_json['path']} in UCI description "
                               "{engine_json_path}, ignoring this engine.")
                continue

            if 'active' not in engine_json or engine_json['active'] is False:
                self.log.debug(f"UCI engine at {engine_json_path} has not property "
                               "'active': true, ignoring this engine.")
                continue

            base_name, _ = os.path.splitext(engine_json_path)
            engine_json_help_path = base_name + "-help.json"
            engine_json['help_path'] = engine_json_help_path
            engine_json['json_path'] = engine_json_path
            name = engine_json['name']
            self.engines[name] = {}
            self.engines[name]['params'] = engine_json
        self.log.debug(f"{len(self.engines)} engine descriptions loaded.")
        # self.publish_uci_engines()

    def publish_uci_engines(self):
        uci_standard_options = ["Threads", "MultiPV", "SyzygyPath", "Ponder",
                                "UCI_Elo", "Hash"]
        engine_list = {}
        for engine in self.engines:
            engine_list[engine] = {}
            engine_list[engine] = {
                "name": self.engines[engine]["params"]["name"],
                "active": self.engines[engine]["params"]["active"],
                "options": {}
            }
            for opt in uci_standard_options:
                if "uci-options" in self.engines[engine]["params"]:
                    if opt in self.engines[engine]["params"]["uci-options"]:
                        engine_list[engine]["options"][opt] = self.engines[engine]["params"]["uci-options"][opt]
        self.appque.put({
            "cmd": "engine_list",
            "actor": self.name,
            "engines": engine_list
        })


class UciAgent:
    """ Support for single UCI chess engine """

    def __init__(self, appque, engine_json, prefs):
        self.active = False
        self.que = appque
        self.engine_json = engine_json
        self.prefs = prefs
        self.name = engine_json['name']
        self.log = logging.getLogger('UciAgent_'+self.name)
        # self.engine = engine_spec['engine']
        # self.ponder_board = None
        self.active = True
        self.busy = False
        self.thinking = False
        self.stopping = False
        # Asyncio queues are not thread-safe, hence useless here.
        self.cmd_que = queue.Queue()
        self.thinking = False
        self.analysisresults = None
        # self.loop=asyncio.new_event_loop()
        self.worker = threading.Thread(target=self.async_agent_thread, args=())
        self.worker.setDaemon(True)
        self.worker.start()
        self.info_throttle = 0.5
        self.version_name = self.name+" 1.0"
        self.authors = ""
        self.engine = None
        self.transport = None
        self.loop_active = False

    async def async_quit(self):
        await self.engine.quit()

    def quit(self):
        # ft = self.engine.terminate(async_callback=True)
        # ft.result()
        asyncio.run(self.async_quit())
        self.active = False

    def agent_ready(self):
        return self.active

    def send_agent_state(self, state, msg=""):
        stmsg = {'cmd': 'agent_state', 'state': state, 'message': msg, 'name': self.version_name,
                 'authors': self.authors, 'class': 'engine', 'actor': self.name}
        self.que.put(stmsg)
        self.log.debug(f"Sent {stmsg}")

    async def uci_open_engine(self):
        try:
            transport, engine = await chess.engine.popen_uci(
                self.engine_json['path'])
            self.engine = engine
            self.transport = transport
            self.log.info(f"Engine {self.name} opened.")
            try:
                if 'name' in self.engine.id:
                    self.version_name = self.engine.id['name']
                if 'author' in self.engine.id:
                    self.authors = self.engine.id['author']
            except Exception as e:
                self.log.error(
                    f"Failed to get engine-id-info {self.engine.id}: {e}")
            self.log.debug(f"Engine id: {self.engine.id}")
        except Exception as e:
            self.log.error(f"Failed to popen UCI engine {self.name} at "
                           "{self.engine_json['path']}, ignoring: {e}")
            self.engine = None
            self.transport = None
            return False

        optsh = {}
        opts = {}
        rewrite_json = False
        if os.path.exists(self.engine_json['json_path']) is False:
            rewrite_json = True
            self.engine_json['uci-options'] = {}
        if 'version' not in self.engine_json or \
           self.engine_json['version'] < UciEngines.ENGINE_JSON_VERSION:
            self.log.error(
                f"{self.engine_json['json_path']} is outdated. Resetting content")
            rewrite_json = True
            self.engine_json['version'] = UciEngines.ENGINE_JSON_VERSION
        if 'uci-options' not in self.engine_json or self.engine_json['uci-options'] == {}:
            rewrite_json = True
            self.engine_json['uci-options'] = {}
        else:
            for opt in self.engine.options:
                if opt not in self.engine_json['uci-options']:
                    entries = self.engine.options[opt]
                    # Ignore buttons
                    if entries.type != 'button':
                        self.log.warning(
                            f'New UCI opt {opt} for {self.name}, reset to defaults')
                        rewrite_json = True

        if rewrite_json is True:
            self.log.info(
                f"Writing defaults for {self.name} to {self.engine_json['json_path']}")
            for opt in self.engine.options:
                entries = self.engine.options[opt]
                optvs = {}
                optvs['name'] = entries.name
                optvs['type'] = entries.type
                optvs['default'] = entries.default
                optvs['min'] = entries.min
                optvs['max'] = entries.max
                optvs['var'] = entries.var
                optsh[opt] = optvs
                # TODO: setting buttons to their default causes python_chess uci
                # to crash (komodo 9), see above
                if entries.type != 'button':
                    opts[opt] = entries.default
            self.engine_json['uci-options'] = opts
            self.engine_json['uci-options-help'] = optsh
            try:
                with open(self.engine_json['json_path'], 'w') as f:
                    json.dump(self.engine_json, f, indent=4)
            except Exception as e:
                self.log.error(
                    f"Can't save engine.json to {self.engine_json['json_path']}, {e}")
            try:
                with open(self.engine_json['help_path'], 'w') as f:
                    json.dump(
                        self.engine_json['uci-options-help'], f, indent=4)
            except Exception as e:
                self.log.error(
                    f"Can't save help to {self.engine_json['help_path']}, {e}")
        else:
            opts = self.engine_json['uci-options']

        auto_opts = ['Ponder', 'MultiPV', 'UCI_Chess960']
        def_opts = copy.deepcopy(opts)
        for op in auto_opts:
            if op in def_opts:
                del def_opts[op]

        await self.engine.configure(def_opts)
        self.log.debug(f"Ping {self.name}")
        await self.engine.ping()
        self.log.debug(f"Pong {self.name}")
        self.send_agent_state('idle')
        return True

    async def async_stop(self):
        if self.stopping is True:
            self.log.warning('Stop aready in progress.')
            return
        if self.thinking is True:
            self.log.info('Initiating async stop')
            self.stopping = True
            if self.analysisresults is not None:
                self.analysisresults.stop()

    async def async_go(self, board, mtime, ponder=False, analysis=False):
        if mtime != -1:
            mtime = mtime/1000.0
        if ponder is True:
            self.log.warning("Ponder not implemented!")
        pv = []
        last_info = []
        self.log.debug(f"mtime: {mtime}")
        if 'MultiPV' in self.engine_json['uci-options']:
            mpv = self.engine_json['uci-options']['MultiPV']
            for i in range(mpv):
                pv.append([])
                last_info.append(0)
                res = {'cmd': 'current_move_info',
                       'multipv_index': i+1,
                       'variant': [],
                       'actor': self.name,
                       'score': ''
                       }
                self.que.put(res)  # reset old evals
        else:
            pv.append([])
            mpv = 1
        if mtime == -1:
            self.log.debug("Infinite analysis")
            lm = None
        else:
            lm = chess.engine.Limit(time=mtime)
        rep = None
        skipped = False
        self.send_agent_state('busy')
        self.log.info(f"Starting UCI {self.name}")
        info = None
        best_score = None
        with await self.engine.analysis(board, lm, multipv=mpv, info=chess.engine.Info.ALL) \
                as self.analysisresults:
            async for info in self.analysisresults:
                if self.stopping is True:
                    self.log.info(f"Stop: request, aborting calc.")
                    break
                self.log.debug(info)
                if 'pv' in info:
                    if 'multipv' in info:
                        ind = info['multipv']-1
                    else:
                        ind = 0
                    pv[ind] = []
                    for mv in info['pv']:
                        pv[ind].append(mv.uci())
                    rep = {'cmd': 'current_move_info',
                           'multipv_index': ind+1,
                           'variant': pv[ind],
                           'actor': self.name
                           }
                    if 'score' in info:
                        try:
                            if info['score'].is_mate():
                                sc = str(info['score'])
                            else:
                                cp = float(str(info['score']))/100.0
                                sc = '{:.2f}'.format(cp)
                        except Exception as e:
                            self.log.error(
                                f"Score transform failed {info['score']}: {e}")
                            sc = '?'
                        rep['score'] = sc
                        if ind == 0:
                            best_score = sc
                    if 'depth' in info:
                        rep['depth'] = info['depth']
                    if 'seldepth' in info:
                        rep['seldepth'] = info['seldepth']
                    if 'nps' in info:
                        rep['nps'] = info['nps']
                    if 'tbhits' in info:
                        rep['tbhits'] = info['tbhits']
                    if time.time()-last_info[ind] > self.info_throttle:
                        self.que.put(rep)
                        last_info[ind] = time.time()
                        skipped = False
                    else:
                        skipped = True

        self.analysisresults = None
        self.log.debug("thinking comes to end")
        if skipped is True and rep is not None:
            self.que.put(rep)
        rep = None
        if len(pv) > 0 and len(pv[0]) > 0:
            if analysis is False:
                move = pv[0][0]
                rep = {'cmd': 'move',
                       'uci': move,
                       'actor': self.name
                       }
                if best_score is not None:
                    rep['score'] = best_score
                if 'depth' in info:
                    rep['depth'] = info['depth']
                if 'seldepth' in info:
                    rep['seldepth'] = info['seldepth']
                if 'nps' in info:
                    rep['nps'] = info['nps']
                if 'tbhits' in info:
                    rep['tbhits'] = info['tbhits']

                self.log.debug(f"Queing result: {rep}")
                self.que.put(rep)
            self.log.info('Calc finished.')
        else:
            self.log.error('Engine returned no move.')
        self.thinking = False
        self.stopping = False
        self.send_agent_state('idle')

    def stop(self):
        self.log.info('synchr stop received')
        if self.thinking is False:
            self.log.debug(f"No need to stop {self.name}, not running.")
        asyncio.run(self.async_stop())

    def go(self, board, mtime, ponder=False, analysis=False):
        self.log.info('go received')
        if self.thinking is True:
            self.log.error(
                f"Can't start engine {self.name}: it's already busy!")
            return False
        self.thinking = True
        self.stopping = False
        cmd = {'board': board, 'mtime': mtime,
               'ponder': ponder, 'analysis': analysis}
        self.cmd_que.put(cmd)
        return True

    async def uci_event_loop(self):
        ok = await self.uci_open_engine()
        self.loop_active = True
        if ok is True:
            while self.loop_active is True:
                try:
                    cmd = self.cmd_que.get_nowait()
                    self.log.debug("Go!")
                    await self.async_go(cmd['board'], cmd['mtime'], ponder=cmd['ponder'],
                                        analysis=cmd['analysis'])
                    self.cmd_que.task_done()
                except queue.Empty:
                    await asyncio.sleep(0.05)
                except Exception as e:
                    self.log.warning(f"Failed to get que: {e}")

    def async_agent_thread(self):
        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(self.uci_event_loop())
