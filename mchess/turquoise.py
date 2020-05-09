''' Turquoise chess main module '''
import argparse
import logging
import json
import importlib
import queue


__version__ = "0.3.0"


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
            'computer': ('async_uci_agent', ['UciEngines', 'UciAgent'])
        }

        self.log = logging.getLogger("TurquoiseStartup")

        # self.imports = {'Darwin': ['chess_link_usb'], 'Linux': [
        #    'chess_link_bluepy', 'chess_link_usb'], 'Windows': ['chess_link_usb']}
        # system = platform.system()

        self.prefs = self.read_preferences(self.preference_version)
        self.config_logging(self.prefs)

        self.main_thread = None
        self.main_event_queue = queue.Queue()

        self.agent_modules={}
        self.agents = {}
        for agent in self.known_agents:
            if agent in self.prefs['agents']:
                try:
                    module = importlib.import_module(self.known_agents[agent][0])
                    self.agent_modules[agent] = module
                except Exception as e:
                    self.log.error(f"Failed to import module {self.known_agents[agent][0]} for agent {agent}: {e}")

    def write_preferences(self, pref):
        try:
            with open("preferences.json", "w") as fp:
                json.dump(pref, fp, indent=4)
        except Exception as e:
            self.log.error(f"Failed to write preferences.json, {e}")

    def set_default_preferences(self, version):
        prefs = {
            "version": version,
            "agents": ["chess_link", "terminal", "web", "tk", "qt", "computer"],
            "default_human_player": {
                "name": "human",
                "location": ""
            },
            "chess_link": {
                "max_plies_board": 3,
                "ply_vis_delay": 80,
                "import_chesslink_position": True,
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
                "chess_engine": "ERROR"
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

    def start_up(self):
        for agent in self.agent_modules:
            class_name = self.known_agents[agent][1]
            if isinstance(class_name, list):
                self.log.error(f"Not yet implemented: {class_name}")
            else:
                try:
                    self.log.info(f"Instantiating agent {agent}, {class_name}")
                    agent_class = getattr(self.agent_modules[agent], class_name)
                    self.agents[agent] = agent_class(self.main_event_queue, self.prefs[agent])
                except Exception as e:
                    self.log.error(f"Failed to instantiate {class_name} for agent {agent}: {e}")


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

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=log_level)
    logger = logging.getLogger('Turquoise')
    logger.setLevel(log_level)
    logger.info("STARTING")
    logger.setLevel(log_level)

    ts = TurquoiseSetup(args)
    ts.start_up()

    # if ts.main_thread is None:

    # mc = Mchess()
    # mc.game_state_machine()
