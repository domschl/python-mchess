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
    ENGINE_JSON_VERSION=1

    def __init__(self, appque, prefs):
        self.log = logging.getLogger("UciEngines")
        self.prefs = prefs
        self.appque = appque

        COMMON_ENGINES = ['stockfish', 'crafty', 'komodo']
        for engine_name in COMMON_ENGINES:
            engine_json_path = os.path.join('engines', engine_name+'.json')
            if os.path.exists(engine_json_path):
                inv=False
                try:
                    with open(engine_json_path) as f:
                        engine_json = json.load(f)
                    if 'version' in engine_json and engine_json['version']==self.ENGINE_JSON_VERSION:
                        inv=False
                    else:
                        self.log.warning(f"Wrong version information in {engine_json_path}")
                        inv=True
                except Exception as e:
                    self.log.error(f"Json engine load of {engine_json_path} failed: {e}")
                    inv=True
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
                    except:
                        self.log.error(
                            f'Failed to write no engine description {engine_json_path}')
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
            except:
                self.log.error(
                    f'Failed to read UCI engine description {engine_json_path}')
                continue
            if 'name' not in engine_json:
                self.log.error(
                    f"Mandatory parameter 'name' is not in UCI description {engine_json_path}, ignoring this engine.")
                continue
            if 'path' not in engine_json:
                self.log.error(
                    f"Mandatory parameter 'path' is not in UCI description {engine_json_path}, ignoring this engine.")
                continue
            if os.path.exists(engine_json['path']) is False:
                self.log.error(
                    f"Invalid path {engine_json['path']} in UCI description {engine_json_path}, ignoring this engine.")
                continue

            if 'active' not in engine_json or engine_json['active'] is False:
                self.log.debug(
                    f"UCI engine at {engine_json_path} has not property 'active': true, ignoring this engine.")
                continue

            base_name, _ = os.path.splitext(engine_json_path)
            engine_json_help_path = base_name + "-help.json"
            engine_json['help_path'] = engine_json_help_path
            engine_json['json_path'] = engine_json_path
            name = engine_json['name']
            self.engines[name] = {}
            self.engines[name]['params'] = engine_json
        self.log.debug(f"{len(self.engines)} engine descriptions loaded.")


class UciAgent:
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
        self.cmd_que = queue.Queue()
        self.thinking = False
        # self.loop=asyncio.new_event_loop()
        self.worker = threading.Thread(target=self.async_agent_thread, args=())
        self.worker.setDaemon(True)
        self.worker.start()
        self.info_throttle=0.5
        self.version_name=self.name+" 1.0"
        self.authors=""

    # async def fake_open(self, filepath):
    #    _, self.engine = await chess.engine.popen_uci(filepath) # engine_spec['engine']

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
        stmsg={'agent-state': state, 'message': msg, 'name': self.version_name, 'authors': self.authors, 'class': 'engine', 'actor': self.name}
        self.que.put(stmsg)
        self.log.debug(f"Sent {stmsg}")

    async def async_stop(self):
        if self.thinking is True:
            self.stopping=True

    async def async_go(self, board, mtime, ponder=False):
        if mtime!=-1:
            mtime = mtime/1000.0
        # _, self.engine = await chess.engine.popen_uci('/usr/local/bin/stockfish')
        # self.log.info(f"{self.name} go, mtime={mtime}, board={board}")
        pv=[]
        last_info=[]
        self.log.info(f"mtime: {mtime}")
        if 'MultiPV' in self.engine_json['uci-options']:
            mpv=self.engine_json['uci-options']['MultiPV']
            for i in range(mpv):
                pv.append([])
                last_info.append(0)
                res={'curmove' : {
                    'multipv_ind': i+1,
                    'variant': [],
                    'actor': self.name,
                    'score': ''
                }}
                self.que.put(res)  # reset old evals
        else:
            pv.append([])
            mpv=1
        self.log.info(f"pv0: {pv}")
        if mtime==-1:
            self.log.info("Infinite analysis")
            lm=None
            self.log.info("Infinite analysis")
        else:
            lm=chess.engine.Limit(time=mtime)
        rep=None
        skipped=False
        self.send_agent_state('busy')
        self.thinking = True
        self.stopping=False
        with await self.engine.analysis(board, lm, multipv=mpv, info=chess.engine.Info.ALL) as analysis:
            # self.log.info(f"RESULT: {result}")
            async for info in analysis:
                if self.stopping is True:
                    self.log.info(f"Analysis aborted.")
                    self.stopping = False
                    break
                # self.log.info(info)
                if 'pv' in info:
                    if 'multipv' in info:
                        ind=info['multipv']-1
                    else:
                        ind=0
                    pv[ind]=info['pv']
                    rep = {'curmove': {
                        'multipv_ind': ind+1,
                        'variant': info['pv'],
                        'actor': self.name
                    }}
                    if 'score' in info:
                        try:
                            if info['score'].is_mate():
                                sc=str(info['score']) # .Mate().score(0)
                            else:
                                cp=float(str(info['score']))/100.0
                                sc='{:.2f}'.format(cp)  # XXX mate? transform pov, /100.0
                        except:
                            self.log.error(f"Score transform failed {info['score']}")
                            sc='?'
                        rep['curmove']['score']=sc
                        self.log.info("stored")
                    if 'depth' in info:
                        rep['curmove']['depth']=info['depth']
                    if 'seldepth' in info:
                        rep['curmove']['seldepth']=info['seldepth']
                    if 'nps' in info:
                        rep['curmove']['nps']=info['nps']
                    if 'tbhits' in info:
                        rep['curmove']['tbhits']=info['tbhits']
                    if time.time()-last_info[ind] > self.info_throttle:
                        self.que.put(rep)
                        last_info[ind]=time.time()
                        skipped=False
                    else:
                        skipped=True

        if skipped is True and rep is not None:
            self.que.put(rep)
        self.log.info(f"pv: {pv}")
        if len(pv)>0 and len(pv[0])>0:
            move=pv[0][0]
            self.log.info("MOVE")
            board.push(move)
            rep = {'move': {
                'uci': move.uci(),
                'actor': self.name
            }}

            if 'score' in info:
                try:
                    if info['score'].is_mate():
                        sc=str(info['score']) # .Mate().score(0)
                    else:
                        cp=float(str(info['score']))/100.0
                        sc='{:.2f}'.format(cp)  # XXX mate? transform pov, /100.0
                except:
                    self.log.error(f"Score transform failed {info['score']}")
                    sc='?'
                rep['move']['score']=sc
                self.log.info("stored")
            if 'depth' in info:
                rep['move']['depth']=info['depth']
            if 'seldepth' in info:
                rep['move']['seldepth']=info['seldepth']
            if 'nps' in info:
                rep['move']['nps']=info['nps']
            if 'tbhits' in info:
                rep['move']['tbhits']=info['tbhits']

            self.log.info(f"Queing result: {rep}")
            self.que.put(rep)
        else:
            self.log.error('Engine returned no move.')
        self.thinking = False
        self.send_agent_state('idle')


    async def uci_open_engine(self):
        try:
            transport, engine = await chess.engine.popen_uci(
                self.engine_json['path'])
            self.engine = engine
            self.transport = transport
            self.log.info(f"Engine {self.name} opened.")
            try:
                if 'name' in self.engine.id:
                    self.version_name=self.engine.id['name']
                if 'author' in self.engine.id:
                    self.authors=self.engine.id['author']
            except Exception as e:
                self.log.error(f"Failed to get engine-id-info {self.engine.id}: {e}")
            self.log.debug(f"Engine id: {self.engine.id}")
        except:
            self.log.error(
                f"Failed to popen UCI engine {self.name} at {self.engine_json['path']}, ignoring this engine.")
            self.engine = None
            self.transport = None
            return False

        optsh = {}
        opts = {}
        rewrite_json = False
        if os.path.exists(self.engine_json['json_path']) is False:
            rewrite_json = True
            self.engine_json['uci-options'] = {}
        if 'version' not in self.engine_json or self.engine_json['version'] < UciEngines.ENGINE_JSON_VERSION:
            self.log.error(f"{self.engine_json['json_path']} is outdated. Resetting content")
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
                            'New UCI option {} for {}, resetting to defaults'.format(opt, self.name))
                        rewrite_json = True

        if rewrite_json is True:
            self.log.info("Writing defaults for {} to {}".format(
                self.name, self.engine_json['json_path']))
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
                # TODO: setting buttons to their default causes python_chess uci to crash (komodo 9), see above
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

        # if 'Ponder' in opts:
        #     self.engines[name]['use_ponder'] = opts['Ponder']
        # else:
        #     self.engines[name]['use_ponder'] = False
        auto_opts = ['Ponder', 'MultiPV', 'UCI_Chess960']
        def_opts=copy.deepcopy(opts)
        for o in auto_opts:
            if o in def_opts:
                del def_opts[o]

        await self.engine.configure(def_opts)
        self.log.info(f"Ping {self.name}")
        await self.engine.ping()
        self.log.info(f"Pong {self.name}")
        self.send_agent_state('idle')
        return True

    async def uci_event_loop(self):
        ok = await self.uci_open_engine()
        self.loop_active = True
        if ok is True:
            while self.loop_active is True:
                try:
                    cmd = self.cmd_que.get_nowait()
                    self.log.debug("Go!")
                    await self.async_go(cmd['board'], cmd['mtime'], cmd['ponder'])
                except:
                    await asyncio.sleep(0.2)  # XXX retest asyncio.queue

    def async_agent_thread(self):
        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(self.uci_event_loop())

    def stop(self):
        self.log.info('stop received')
        asyncio.run(self.async_stop())

    def go(self, board, mtime, ponder=False):
        self.log.info('cmd_que put:')
        self.cmd_que.put({'board': board, 'mtime': mtime, 'ponder': ponder})
