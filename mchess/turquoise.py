''' Turquoise chess main module '''
import argparse
import logging
import json
import importlib


__version__ = "0.3.0"


class TurquoiseSetup():
    ''' Load configuration and prepare agent initialization '''

    def __init__(self):
        self.preference_version = 1

        self.log = logging.getLogger("TurquoiseStartup")

        # self.imports = {'Darwin': ['chess_link_usb'], 'Linux': [
        #    'chess_link_bluepy', 'chess_link_usb'], 'Windows': ['chess_link_usb']}
        # system = platform.system()

        self.prefs = self.read_preferences(self.preference_version)
        self.bg_agents = []
        self.fg_agent = None

        if 'chesslink' in self.prefs['agents']:
            self.chess_link_agent_module = importlib.import_module(
                'chess_link_agent')
            # import ChessLinkAgent
        else:
            self.chess_link_agent_module = None
        if 'terminal' in self.prefs['agents']:
            self.terminal_agent_module = importlib.import_module(
                'terminal_agent')
            # import TerminalAgent
        else:
            self.terminal_agent_module = None
        if 'tk' in self.prefs['agents']:
            self.tk_agent_module = importlib.import_module('tk_agent')
            # import TkAgent
        else:
            self.tk_agent_mdule = None
        if 'web' in self.prefs['agents']:
            self.web_agent_module = importlib.import_module('web_agent')
            #import WebAgent
        else:
            self.web_agent_module = None
        if 'computer' in self.prefs['agents']:
            self.computer_module = importlib.import_module('async_uci_agent')
            # import UciAgent, UciEngines
        else:
            self.computer_module = None

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
                    "stockfish", "lc0", "komodo"
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
            self.prefs = self.set_default_preferences(version)
            self.write_preferences(self.prefs)
        '''
        if 'think_ms' not in prefs:
            prefs['think_ms'] = 500
            changed_prefs = True
        if 'use_unicode_figures' not in prefs:
            prefs['use_unicode_figures'] = True
            changed_prefs = True
        if 'invert_term_color' not in prefs:
            prefs['invert_term_color'] = False
            changed_prefs = True
        if 'max_plies_terminal' not in prefs:
            prefs['max_plies_terminal'] = 6
            changed_prefs = True
        if 'max_plies_board' not in prefs:
            prefs['max_plies_board'] = 3
            changed_prefs = True
        if 'ply_vis_delay' not in prefs:
            prefs['ply_vis_delay'] = 80
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
        if 'active_agents' not in prefs:
            prefs['active_agents'] = {
                "human": ["chess_link", "terminal", "web", "tk"],
                "computer": ["stockfish", "lc0"]
            }
            changed_prefs = True
        if 'log_levels' not in prefs:
            prefs['log_levels'] = {
                'chess.engine': 'ERROR'
            }
            changed_prefs = True
        if changed_prefs is True:
            self.write_preferences(prefs)
            '''
        return prefs


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
        log_level_e = logging.DEBUG
        log_level_pce = logging.DEBUG
    else:
        log_level = logging.WARNING
        log_level_e = logging.ERROR
        log_level_pce = logging.ERROR

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=log_level)
    logger.setLevel(logging.INFO)
    logger = logging.getLogger('Turquoise')
    logger.info("STARTING")
    logger.setLevel(log_level)

    ts = TurquoiseSetup()
    # mc = Mchess()
    # mc.game_state_machine()
