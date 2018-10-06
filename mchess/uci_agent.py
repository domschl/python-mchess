import logging
import queue
import json
import chess.uci


class UciEngines:
    """Search for UCI engines and make a list of all available engines
    """

    def __init__(self):
        self.log = logging.getLogger("UciEngines")

        COMMON_ENGINES = ['stockfish', 'crafty', 'komodo']
        try:
            with open('uci_engines.json', 'r') as f:
                self.engines = json.load(f)
                logging.debug(self.engines)
        except Exception as e:
            logging.error("Can't load uci_engines.json: {}".format(e))
            return

        self.log.debug('{} engines loaded.'.format(len(self.engines)))
        if len(self.engines['engines']) == 0:
            logging.error("No engine defined! Check uci_engines.json.")


class UciAgent:
    def __init__(self, appque):
        self.active = False
        self.name = 'UciAgent'
        self.log = logging.getLogger("UciAgent")
        self.appque = appque
        self.ponder_board = None

        try:
            with open('uci_engines.json', 'r') as f:
                self.engines = json.load(f)
                logging.debug(self.engines)
        except Exception as e:
            logging.error("Can't load uci_engines.json: {}".format(e))
            return

        self.log.debug('{} engines loaded.'.format(len(self.engines)))
        if len(self.engines['engines']) == 0:
            logging.error("No engine defined! Check uci_engines.json.")

        engine_no = 0
        # TODO: Error checking!
        if 'default-engine' in self.engines:
            engine_no = self.engines['default-engine']
            if engine_no > len(self.engines['engines']):
                engine_no = 0
        self.engine = chess.uci.popen_engine(
            self.engines['engines'][engine_no]['path'])
        logging.debug('Loading engine {}.'.format(
            self.engines['engines'][engine_no]['name']))
        self.name = self.engines['engines'][engine_no]['name']
        self.uci_handler(self.engine)
        self.engine.uci()
        optsh = {}
        opts = {}
        if 'uci-options' not in self.engines['engines'][engine_no] or self.engines['engines'][engine_no]['uci-options'] == {}:
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
                opts[opt] = entries.default
            self.engines['engines'][engine_no]['uci-options'] = opts
            self.engines['engines'][engine_no]['uci-options-help'] = optsh
            try:
                with open('uci_engines.json', 'w') as f:
                    json.dump(self.engines, f)
            except Exception as e:
                logging.error(
                    "Can't save prefs to uci_engines.json, {}".format(e))
        else:
            opts = self.engines['engines'][engine_no]['uci-options']

        print("Setting uci:")
        print(opts)

        if 'Ponder' in opts:
            self.use_ponder = opts['Ponder']
        else:
            self.use_ponder = False

        self.engine.setoption(opts)

        self.engine.isready()
        self.active = True

    def agent_ready(self):
        return self.active

    def go(self, board, mtime, ponder=False):
        self.engine.position(board)
        self.last_board = board
        if mtime == 0:
            self.engine.go(infinite=True, async_callback=True, ponder=ponder)

        else:
            self.engine.go(movetime=mtime,
                           async_callback=True, ponder=ponder)

    class UciHandler(chess.uci.InfoHandler):
        def __init__(self):
            self.que = None
            self.name = 'UciAgent'
            self.last_pv_move = ""
            self.log = logging.getLogger('UciHandler')
            self.cdepth = None
            self.cseldepth = None
            self.cscore = None
            self.cnps = None
            super().__init__()

        def post_info(self):
            # Called whenever a complete info line has been processed.
            # print(self.info)
            super().post_info()  # Release the lock

        def on_bestmove(self, bestmove, ponder):
            self.log.debug("Best: {}, ponder: {}".format(bestmove, ponder))
            rep = {'move': {
                'uci': bestmove.uci(),
                'actor': self.name
            }}
            if self.cdepth is not None:
                rep['move']['depth'] = self.cdepth
            if self.cseldepth is not None:
                rep['move']['seldepth'] = self.cseldepth
            if self.cnps is not None:
                rep['move']['nps'] = self.cnps
            if self.cscore is not None:
                rep['move']['score'] = self.cscore
            if self.ctbhits is not None:
                rep['move']['tbhits'] = self.ctbhits
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

            super().on_bestmove(bestmove, ponder)

        def score(self, cp, mate, lowerbound, upperbound):
            self.que.put({'score': {'cp': cp, 'mate': mate}})
            if mate is not None:
                self.cscore = '#{}'.format(mate)
            else:
                self.cscore = '{:.2f}'.format(float(cp)/100.0)
            super().score(cp, mate, lowerbound, upperbound)

        def pv(self, moves):
            # variant = []
            # svar = ""
            # for m in moves:
            #     variant.append(m.uci())
            #     svar += m.uci()+" "
            # if svar[-1] == " ":
            #     svar = svar[:-1]
            rep = {'curmove': {
                'variant': moves,
                # 'variant string': svar,
                'actor': self.name
            }}
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
            self.que.put(rep)
            super().pv(moves)

        def depth(self, n):
            self.cdepth = n
            self.que.put({'depth': n})
            super().depth(n)

        def seldepth(self, n):
            self.cseldepth = n
            self.que.put({'seldepth': n})
            super().seldepth(n)

        def nps(self, n):
            self.cnps = n
            self.que.put({'nps': n})
            super().nps(n)

        def tbhits(self, n):
            self.ctbhits = n
            self.que.put({'tbhits': n})
            super().tbhits(n)

    def uci_handler(self, engine):
        self.info_handler = self.UciHandler()
        self.info_handler.name = self.name
        self.info_handler.que = self.appque
        engine.info_handlers.append(self.info_handler)
