import logging
import queue
import json
import chess.uci


class UciAgent:
    def __init__(self, appque):
        self.log = logging.getLogger("UciAgent")
        self.appque = appque

    def load_engines(self):
        with open('uci_engines.json', 'r') as f:
            self.engines = json.load(f)
            logging.debug(self.engines)
            return self.engines

    class UciHandler(chess.uci.InfoHandler):
        def __init__(self):
            self.que = None
            self.last_pv_move = ""
            self.log = logging.getLogger('UciHandler')
            super().__init__()

        def post_info(self):
            # Called whenever a complete info line has been processed.
            # print(self.info)
            super().post_info()  # Release the lock

        def on_bestmove(self, bestmove, ponder):
            self.log.debug("Best: {}".format(bestmove))
            self.que.put({'move': {
                'uci': bestmove.uci(),
                'actor': 'uci-engine'
            }})
            self.last_pv_move = ""
            super().on_bestmove(bestmove, ponder)

        def score(self, cp, mate, lowerbound, upperbound):
            self.que.put({'score': {'cp': cp, 'mate': mate}})
            super().score(cp, mate, lowerbound, upperbound)

        def pv(self, moves):
            variant = []
            svar = ""
            for m in moves:
                variant.append(m.uci())
                svar += m.uci()+" "
            if svar[-1] == " ":
                svar = svar[:-1]
            self.que.put({'curmove': {
                'variant': variant,
                'variant string': svar,
                'actor': 'uci-engine'
            }})
            super().pv(moves)

        def depth(self, n):
            self.que.put({'depth': n})
            super().depth(n)

        def seldepth(self, n):
            self.que.put({'seldepth': n})
            super().seldepth(n)

        def nps(self, n):
            self.que.put({'nps': n})
            super().nps(n)

    def uci_handler(self, engine):
        self.info_handler = self.UciHandler()
        self.info_handler.que = self.appque
        engine.info_handlers.append(self.info_handler)
