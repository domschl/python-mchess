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


'''
    def debris():
        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(self.open_ucis())

        self.log.info("Starting ping timer...")
        self.timer_sec = 0.05
        self.loop = asyncio.get_event_loop()
        thr = threading.Timer(self.timer_sec, self.timer_thread)
        thr.daemon = True
        thr.start()

        # self.worker = threading.Thread(target=self.async_uci_thread, args=())
        # self.worker.setDaemon(True)
        # self.worker.start()
        # self.opened=False
        # while self.opened is False:
        #     time.sleep(0.5)
        #     self.log.debug("Waiting for engines...")

    # def async_uci_thread(self):
    #     self.log.info("calling open_ucis via asyncio.run()")
    #     asyncio.run(self.open_ucis())
    #     self.log.info("done open_ucis!")

    # async def async_ping(self):
    #     for e in self.engines:
    #         self.log.debug(f"thr ping {e}")
    #         await self.engines[e]['engine'].ping()
    #         self.log.debug(f"thr pong {e}")

    # def timer_thread(self):
    #     self.log.info("T-Thr")
    #     asyncio.set_event_loop(self.loop)
    #     asyncio.run(self.async_ping())
    #     # cur_time = time.time()
    #     thr = threading.Timer(self.timer_sec, self.timer_thread)
    #     thr.daemon = True
    #     thr.start()

    # async def open_ucis(self):
    #     self.log.info("entered open_ucis()")
    #     tasks=[]
    #     for engine_json_path in self.engine_json_list:
    #         self.log.info(f"Open UCIs: {engine_json_path}")
    #         if '-help.json' in engine_json_path or 'engine-template.json' in engine_json_path:
    #             continue
    #         self.log.debug(f'Checking UCI engine {engine_json_path}')
    #         tasks.append(asyncio.create_task(self.open_engine(engine_json_path)))
    #     for task in tasks:
    #         await task
    #     self.log.info("opening done.")
    #     self.opened=True

    async def open_engine(self, engine_json_path):
        try:
            with open(engine_json_path, 'r') as f:
                engine_json = json.load(f)
        except:
            self.log.error(
                f'Failed to read UCI engine description {engine_json_path}')
            return False
        if 'name' not in engine_json:
            self.log.error(
                f"Mandatory parameter 'name' is not in UCI description {engine_json_path}, ignoring this engine.")
            return False
        if 'path' not in engine_json:
            self.log.error(
                f"Mandatory parameter 'path' is not in UCI description {engine_json_path}, ignoring this engine.")
            return False
        if os.path.exists(engine_json['path']) is False:
            self.log.error(
                f"Invalid path {engine_json['path']} in UCI description {engine_json_path}, ignoring this engine.")
            return False

        if 'active' not in engine_json or engine_json['active'] is False:
            self.log.debug(
                f"UCI engine at {engine_json_path} has not property 'active': true, ignoring this engine.")
            return False

        base_name, _ = os.path.splitext(engine_json_path)
        engine_json_help_path = base_name + "-help.json"
        name = engine_json['name']
        self.engines[name] = {}
        self.engines[name]['params'] = engine_json

        # ----
        try:
            transport, engine = await chess.engine.popen_uci(
                engine_json['path'])
            self.engines[name]['engine'] = engine
            self.engines[name]['transport'] = transport
            self.log.info(f"Engine {name} opened.")
        except:
            self.log.error(
                f'Failed to popen UCI engine {name} at {engine_json_path}, ignoring this engine.')
            return False

        # XXX

        self.engines[name]['info_handler'] = self.UciHandler()
        self.engines[name]['info_handler'].name = name
        self.engines[name]['info_handler'].active = True
        self.engines[name]['info_handler'].que = self.appque
        # self.engines[name]['engine'].info_handlers.append(
        #    self.engines[name]['info_handler'])

        # self.engines[name]['engine'].uci()

        optsh = {}
        opts = {}
        rewrite_json = False
        if os.path.exists(engine_json_path) is False:
            rewrite_json = True
            self.engines[name]['params']['uci-options'] = {}
        if 'uci-options' not in self.engines[name]['params'] or self.engines[name]['params']['uci-options'] == {}:
            rewrite_json = True
            self.engines[name]['params']['uci-options'] = {}
        else:
            for opt in self.engines[name]['engine'].options:
                if opt not in self.engines[name]['params']['uci-options']:
                    entries = self.engines[name]['engine'].options[opt]
                    # Ignore buttons
                    if entries.type != 'button':
                        self.log.warning(
                            'New UCI option {} for {}, resetting to defaults'.format(opt, name))
                        rewrite_json = True

        if rewrite_json is True:
            self.log.info("Writing defaults for {} to {}".format(
                name, engine_json_path))
            for opt in self.engines[name]['engine'].options:
                entries = self.engines[name]['engine'].options[opt]
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
            self.engines[name]['params']['uci-options'] = opts
            self.engines[name]['uci-options-help'] = optsh
            try:
                with open(engine_json_path, 'w') as f:
                    json.dump(self.engines[name]['params'], f, indent=4)
            except Exception as e:
                self.log.error(
                    f"Can't save engine.json to {engine_json_path}, {e}")
            try:
                with open(engine_json_help_path, 'w') as f:
                    json.dump(self.engines[name]
                              ['uci-options-help'], f, indent=4)
            except Exception as e:
                self.log.error(
                    f"Can't save help to {engine_json_help_path}, {e}")
        else:
            opts = self.engines[name]['params']['uci-options']

        # if 'Ponder' in opts:
        #     self.engines[name]['use_ponder'] = opts['Ponder']
        # else:
        #     self.engines[name]['use_ponder'] = False
        auto_opts = ['Ponder', 'MultiPV', 'UCI_Chess960']
        for o in auto_opts:
            if o in opts:
                del opts[o]

        await self.engines[name]['engine'].configure(opts)
        time.sleep(0.1)

        self.log.info(f"Ping {name}")
        await self.engines[name]['engine'].ping()
        self.log.info(f"Pong {name}")
        # asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        # self.engines[name]['engine'].isready()
'''

'''
    class UciHandler():
        def __init__(self):
            self.que = None
            self.name = 'UciAgent'
            self.last_pv_move = ""
            self.log = logging.getLogger(self.name)
            self.cdepth = None
            self.cseldepth = None
            self.cscore = None
            self.cnps = None
            self.mpv_num = 1
            self.que_cache = {}
            self.que_cache_time = 2.0
            self.que_timer_sec = 1.0
            thr = threading.Timer(self.que_timer_sec, self.que_timer)
            thr.daemon = True
            thr.start()

        def que_timer(self):
            cur_time = time.time()
            keys = list(self.que_cache.keys())
            for key in keys:
                if cur_time-self.que_cache[key]['timestamp'] > self.que_cache_time:
                    self.que.put(self.que_cache[key])
                    del self.que_cache[key]
            thr = threading.Timer(self.que_timer_sec, self.que_timer)
            thr.daemon = True
            thr.start()

        def empty_que_cache(self):
            for msg in self.que_cache:
                self.que.put(self.que_cache[msg])
            self.que_cache = {}

        def post_info(self):
            pass
            # Called whenever a complete info line has been processed.
            # print(self.info)
            # super().post_info()  # Release the lock

        def on_bestmove(self, bestmove, ponder):
            self.log.debug("Best: {}, ponder: {}".format(bestmove, ponder))
            rep = {'move': {
                'uci': bestmove.uci(),
                'actor': self.name
            }}
            # with self:
            #     if 1 in self.info["score"]:
            #         score = self.info["score"][1].cp
            #         mate = self.info["score"][1].mate
            #         if mate is not None:
            #             rep['move']['score'] = '#{}'.format(mate)
            #         else:
            #             rep['move']['score'] = '{:.2f}'.format(
            #                 float(score)/100.0)

            # if self.cdepth is not None:
            #     rep['move']['depth'] = self.cdepth
            # if self.cseldepth is not None:
            #     rep['move']['seldepth'] = self.cseldepth
            # if self.cnps is not None:
            #     rep['move']['nps'] = self.cnps
            # if self.cscore is not None:
            #     rep['move']['score'] = self.cscore
            # if self.ctbhits is not None:
            #     rep['move']['tbhits'] = self.ctbhits
            if ponder is not None:
                rep['move']['ponder'] = ponder.uci()
                self.ponder = ponder.uci()
            else:
                self.ponder = None
            self.que.put(rep)
            self.last_pv_move = ""
            self.cdepth = None
            self.cseldepth = None
            self.cscore = None
            self.cnps = None
            self.ctbhits = None
            self.mpv_num = 1
            self.que_cache = {}

            # super().on_bestmove(bestmove, ponder)

        def score(self, cp, mate, lowerbound, upperbound):
            # if self.last_board.turn == chess.BLACK:
            #     cp = cp*-1
            #     if mate is not None:
            #         mate = mate*-1

            self.que.put({'score': {'cp': cp, 'mate': mate}})
            if mate is not None:
                self.cscore = '#{}'.format(mate)
            else:
                self.cscore = '{:.2f}'.format(float(cp)/100.0)
            # super().score(cp, mate, lowerbound, upperbound)

        def multipv(self, num):
            self.mpv_num = num
            # super().multipv(num)

        def pv(self, moves):
            rep = {'curmove': {
                'multipv_ind': self.mpv_num,
                'variant': moves,
                'actor': self.name
            }}
            que_key = '{}-{}'.format(self.name, self.mpv_num)

            if self.cdepth is not None:
                rep['curmove']['depth'] = self.cdepth
            if self.cseldepth is not None:
                rep['curmove']['seldepth'] = self.cseldepth
            if self.cnps is not None:
                rep['curmove']['nps'] = self.cnps
            if self.cscore is not None:
                rep['curmove']['score'] = self.cscore
            if self.ctbhits is not None:
                rep['curmove']['tbhits'] = self.ctbhits
            if que_key not in self.que_cache:
                rep['timestamp'] = time.time()
            else:
                rep['timestamp'] = self.que_cache[que_key]['timestamp']
            self.que_cache[que_key] = rep
            # self.que.put(rep)
            # super().pv(moves)

        def depth(self, n):
            self.cdepth = n
            self.que.put({'depth': n})
            # super().depth(n)

        def seldepth(self, n):
            self.cseldepth = n
            self.que.put({'seldepth': n})
            # super().seldepth(n)

        def nps(self, n):
            self.cnps = n
            self.que.put({'nps': n})
            # super().nps(n)

        def tbhits(self, n):
            self.ctbhits = n
            self.que.put({'tbhits': n})
            # super().tbhits(n)
'''


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
        # self.loop=asyncio.new_event_loop()
        self.worker = threading.Thread(target=self.async_agent_thread, args=())
        self.worker.setDaemon(True)
        self.worker.start()

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

    async def async_stop(self):
        self.stopped=True

    async def async_go(self, board, mtime, ponder=False):
        if mtime!=-1:
            mtime = mtime/1000.0
        self.stopped=False
        # _, self.engine = await chess.engine.popen_uci('/usr/local/bin/stockfish')
        # self.log.info(f"{self.name} go, mtime={mtime}, board={board}")
        pv=[]
        self.log.info(f"mtime: {mtime}")
        if 'MultiPV' in self.engine_json['uci-options']:
            mpv=self.engine_json['uci-options']['MultiPV']
            for _ in range(mpv):
                pv.append([])
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
        with await self.engine.analysis(board, lm, multipv=mpv, info=chess.engine.Info.ALL) as analysis:
            # self.log.info(f"RESULT: {result}")
            async for info in analysis:
                if self.stopped is True:
                    self.log.info(f"Analysis aborted.")
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
            self.log.info(f"Queing result: {rep}")
            self.que.put(rep)
        else:
            self.log.error('Engine returned no move.')
        

    async def uci_open_engine(self):
        try:
            transport, engine = await chess.engine.popen_uci(
                self.engine_json['path'])
            self.engine = engine
            self.transport = transport
            self.log.info(f"Engine {self.name} opened.")
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
        '''
        # asyncio.run(self.fake_open('/usr/local/bin/stockfish'))
        self.log.info("Start a-run")
        # asyncio.set_event_loop(self.loop)
        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(self.do_go(board, mtime))
        self.log.info("Left a-run")
        # self.engine.position(board)
        # self.last_board = board
        # if mtime == 0:
        #     self.engine.go(infinite=True,
        #                    async_callback=True, ponder=ponder)
        # else:
        #     self.engine.go(movetime=mtime,
        #                    async_callback=True, ponder=ponder)
'''
