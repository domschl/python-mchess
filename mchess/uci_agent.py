import logging
import queue
import json
import chess.uci


class UciAgent:
    def __init__(self, appque):
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
        if 'default-engine' in self.engines:
            engine_no = self.engines['default-engine']
            if engine_no > len(self.engines['engines']):
                engine_no = 0
        self.engine = chess.uci.popen_engine(
            self.engines['engines'][engine_no]['path'])
        logging.debug('Loading engine {}.'.format(
            self.engines['engines'][engine_no]['name']))
        self.name = self.engines['engines'][engine_no]['name']
        self.use_ponder = self.engines['engines'][engine_no]['ponder']
        self.uci_handler(self.engine)
        self.engine.uci()
        # TODO: uci options
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

    def uci_handler(self, engine):
        self.info_handler = self.UciHandler()
        self.info_handler.name = self.name
        self.info_handler.que = self.appque
        engine.info_handlers.append(self.info_handler)
