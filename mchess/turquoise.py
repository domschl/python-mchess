''' Turquoise chess main module '''
import argparse
import logging
import json
import importlib
import queue

from turquoise_dispatch import TurquoiseDispatcher


__version__ = "0.4.0"


class TurquoiseSetup():
    ''' Load configuration and prepare agent initialization '''

    def __init__(self, args):
        self.args = args
        self.preference_version = 1

        # Entries: 'config_name': ('module_name', 'class(es)')
        self.known_agents = {
            'chesslink': ('chess_link_agent', 'ChessLinkAgent'),
            'terminal': ('terminal_agent', 'TerminalAgent'),
            'tk': ('tk_agent', 'TkAgent'),
            'qt': ('qt_agent', 'QtAgent'),
            'web': ('web_agent', 'WebAgent'),
            'aweb': ('async_web_agent', 'AsyncWebAgent'),
            'computer': ('async_uci_agent', ['UciEngines', 'UciAgent'])
        }

        self.log = logging.getLogger("TurquoiseStartup")

        # self.imports = {'Darwin': ['chess_link_usb'], 'Linux': [
        #    'chess_link_bluepy', 'chess_link_usb'], 'Windows': ['chess_link_usb']}
        # system = platform.system()

        self.prefs = self.read_preferences(self.preference_version)
        self.config_logging(self.prefs)

        self.main_thread = None
        self.dispatcher = None
        self.main_event_queue = queue.Queue()

        self.agent_modules = {}
        self.uci_engine_configurator = None
        self.agents = {}
        self.engines = {}
        for agent in self.known_agents:
            if agent in self.prefs['agents']:
                try:
                    module = importlib.import_module(
                        self.known_agents[agent][0])
                    self.agent_modules[agent] = module
                except Exception as e:
                    self.log.error(
                        f"Failed to import module {self.known_agents[agent][0]} for agent {agent}: {e}")

    def write_preferences(self, pref):
        try:
            with open("preferences.json", "w") as fp:
                json.dump(pref, fp, indent=4)
        except Exception as e:
            self.log.error(f"Failed to write preferences.json, {e}")

    def set_default_preferences(self, version):
        prefs = {
            "version": version,
            "agents": ["chesslink", "terminal", "web", "aweb", "computer"],
            "default_human_player": {
                "name": "human",
                "location": ""
            },
            "chesslink": {
                "max_plies_board": 3,
                "ply_vis_delay": 80,
                "import_position": True,
                "autodetect": True,
                "orientation": True,
                "btle_iface": 0,
                "protocol_debug": False,
                "bluetooth_address": "",
                "usb_port": "",
                "transport": ""
            },
            "terminal": {
                "use_unicode_figures": True,
                "invert_term_color": False,
                "max_plies_terminal": 10
            },
            "web": {
                "port": 8001,
                "bind_address": "localhost",
                "tls": False,
                "private_key": "",
                "public_key": ""
            },
            "aweb": {
                "port": 8001,
                "bind_address": "localhost",
                "tls": False,
                "private_key": "",
                "public_key": ""
            },
            "tk": {
                "main_thread": False
            },
            "qt": {
                "main_thread": True
            },
            "computer": {
                "think_ms": 500,
                "default_player": "stockfish",
                "default_2nd_analyser": "lc0",
                "engines": [
                    "stockfish"
                ]
            },
            "log_levels": {
                "chess.engine": "ERROR"
            }
        }
        return prefs

    def read_preferences(self, version):
        prefs = {}
        default_prefs = False
        try:
            with open('preferences.json', 'r') as f:
                prefs = json.load(f)
        except Exception as e:
            default_prefs = True
            self.log.warning(
                f'Failed to read preferences.json: {e}')
        if 'version' not in prefs:
            default_prefs = True
        else:
            if prefs['version'] < version:
                self.log.warning(
                    'preferences.json file is outdated, initializing default values.')
                default_prefs = True

        if default_prefs is True:
            prefs = self.set_default_preferences(version)
            self.write_preferences(prefs)
        return prefs

    def config_logging(self, prefs):
        if 'log_levels' in prefs:
            for module in prefs['log_levels']:
                level = logging.getLevelName(prefs['log_levels'][module])
                logi = logging.getLogger(module)
                logi.setLevel(level)
        else:
            self.log.warning('Custom log levels not defined')

    def main(self):
        for agent in self.agent_modules:
            class_name = self.known_agents[agent][1]
            if isinstance(class_name, list):
                if class_name[0] == 'UciEngines':
                    self.uci_engine_configurator = self.agent_modules[agent].UciEngines(
                        self.main_event_queue, self.prefs[agent])
                    for engine in self.uci_engine_configurator.engines:
                        self.log.info(f"Found engine {engine}")
                        engine_json = self.uci_engine_configurator.engines[engine]['params']
                        if engine == self.prefs['computer']['default_player']:
                            self.log.info(f"{engine} is default-engine")
                            self.agents['uci1'] = self.agent_modules[agent].UciAgent(
                                self.main_event_queue, engine_json, self.prefs['computer'])
                            if self.agents['uci1'] is None:
                                self.log.error(
                                    f'Failed to instantiate {engine}')
                        if engine == self.prefs['computer']['default_2nd_analyser']:
                            self.log.info(f"{engine} is 2nd-engine")
                            self.agents['uci2'] = self.agent_modules[agent].UciAgent(
                                self.main_event_queue, engine_json, self.prefs['computer'])
                            if self.agents['uci2'] is None:
                                self.log.error(
                                    f'Failed to instantiate {engine}')
                        # XXX: startup 1..n engine-agents ?!
                else:
                    self.log.error(f"Not yet implemented: {class_name}")
            else:
                try:
                    self.log.info(f"Instantiating agent {agent}, {class_name}")
                    agent_class = getattr(
                        self.agent_modules[agent], class_name)
                    self.agents[agent] = agent_class(
                        self.main_event_queue, self.prefs[agent])
                except Exception as e:
                    self.log.error(
                        f"Failed to instantiate {class_name} for agent {agent}: {e}")

        # mainthreader id
        self.dispatcher = TurquoiseDispatcher(
            self.main_event_queue, self.prefs, self.agents, self.uci_engine_configurator)

        try:
            self.dispatcher.game_state_machine_NEH()
        except KeyboardInterrupt:
            self.dispatcher.quit()


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
    else:
        log_level = logging.INFO

    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(message)s',
                        level=log_level, filename='turquoise.log', filemode='w')

    # console = logging.StreamHandler()
    # console.setLevel(logging.INFO)

    logger = logging.getLogger('Turquoise')

    logger.setLevel(log_level)
    logger.info("---------------------------------")
    logger.info("STARTING")
    logger.setLevel(log_level)

    ts = TurquoiseSetup(args)
    ts.main()
