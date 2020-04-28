# python-mchess

![Alpha status](https://img.shields.io/badge/Project%20status-Alpha-red.svg)
[![License](http://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-dev-blue.svg)](https://domschl.github.io/python-mchess/doc/build/html/index.html)

`python-mchess` is a collections of libraries to work with Millennium's Chess Genius Exclusive chess board via the Chess Link interface.

It provides two layers of functionality:

* A hardware driver for the Chess Genius Exclusive chess board, supporting piece recognition and leds via USB or Bluetooth LE
* A sample implementation to connect arbitrary UCI engines to the chess board.

Currently, the following platforms are under development:

|              | Linux | Raspberry Pi | macOS | Windows |
| ------------ | ----- | ------------ | ----- | ------- |
| USB          | x     | x            | x     | x       |
| Bluetooth LE | x     | x            |       |

## Alpha installation instructions

This project is under heavy development, and basically everything described below might change at some point.

### Dependencies

`python-mchess` is written for Python >= 3.7. 
If UCI-engine support (python-chess dependecy) is not used, any Python 3.x works. (python-mchess makes use of latest async features of Python 3.7 and later)

`python-mchess` board driver for Chess Link depends on `PySerial` and (Linux/Raspberry Pi only) `BluePy`


#### Optional UCI engine support

In order to use UCI engines with mchess, additionally `python-chess` is used.

```bash
pip3 install pyserial [bluepy] [python-chess]
```

Then clone the repository

```bash
git clone https://github.com/domschl/python-mchess
```

Now configure some engines:

```bash
cd mchess/engines
```

Copy `engine-template.json` for each UCI engine to a file `<engine-name>.json`, and edit the fields `'name'` and `'path'`. 

A sample content for stockfish in Linux would be: 
`engines/stockfish.json`:

```json
{
    "name": "stockfish",
    "path": "/usr/bin/stockfish",
    "active": true
}
```

Note: Windows users need to use paths with `\\` or `/` for proper json encoding.

#### Web client

The web agent requires python modules `Flask`, `Flask-Sockets` and `gevent`.

```bash
pip3 install flask flask-sockets gevent
```

Node JS packet manager `npm` is needed to install the javascript dependencies:

```bash
cd mchess/web
npm install
```

This installs the dependency `cm-chessboard`.

### Start

Then in directory `mchess`, simply start from console:

```bash
python3 mchess.py
```

This will start chess agents for the chess board, automatically detecting board hardware via USB or BLuetooth LE (Linux, Raspberry PI only), and load the [first active] UCI engine (testet with Leela Chess Zero (Lc0) and Stockfish 9).

Enter `help` in terminal to get an overview of available console commands (e.g. switch sides, take back moves, analyze position).

The web client can be reached at `http://localhost:8001`. From remote use `http://computer-name:8001`.

![Early alpha web preview](https://raw.github.com/domschl/python-mchess/master/images/WebClientAlpha.png)
_Early alpha preview of web client "Turquoise"_

Note: Bluetooth LE hardware detection either requires admin privileges for the one-time intial bluetooth scan, or the `setcap` command below.

#### Bluetooth LE board search without `sudo`

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' PATH/TO/LIB/python3._x_/site-packages/bluepy/bluepy-helper

# The simply start mchess, scanning is started automatically:
python3 mchess.py
```

#### Bluetooth LE board search with `sudo`

If the above fails, try to scan once with `sudo`:

```bash
sudo python3 mchess.py
```

If `mchess.py` has been started with `sudo`, it is advisible to change the ownership of `chess_link_config.json` to the user account that is used for games, otherwise `mchess.py` cannot update the configuration (e.g. orientation changes) automatically.

Restart the program, once the board has connected (the connection address is saved in `chess_link_config.json`)

Do NOT use `sudo` on subsequent starts, or the communication might fail. If scan was executed with `sudo`, then you might want to set ownership for `chess_link_config.json` to your user-account, since the file will be rewritten, if the detected board orientation is changed. (`chown your-username chess_link_config.json`)

All engine descriptions in directory 'engines' will now contain the default-UCI options for each engine. Those can be edited e.g. to enable tablebases or other UCI options.


![Console mchess](https://raw.github.com/domschl/python-mchess/master/images/MchessAlpha.png)
_Console output of python module, allows terminal interactions: enter 'help' for an overview of console commands_

## Usage

On start, the current position from Chess Genius Exclusive board is imported and displayed on the console.
Simply start making a move on the board, and the UCI engine will reply. During the time, the engine calculates,
the best current line is displayed on the board for up to 3 half-moves (see `preferences.json` to enable/disable this
feature).

Enter `help` on the terminal console to get an overview of commands, and see below for more customization options

## Customization

Currrently, there doesn't exist much of a GUI to configure `mchess`, and configuration relies on a number of JSON files.

### `preferences.json`, general options for mchess

| Field                | Default  | Description                                             |
| -------------------- | -------- | --------------------------------------------------------|
| `think_ms`           | `500`    | Number of milli seconds, computer calculates for a move. Better level configuration will be added at a later point. |
| `use_unicode_figures`| `true`   | Most terminals can display Unicode chess figures, if that doesn't work, set to `false`, and letters are used for chess pieces instead.|
| `invert_term_color`  | `false`  | How chess board colors black and white are displayed might depend on the background color of your terminal. Change, if black and white are mixed up. |
| `max_plies_terminal` | `6`      | The number of half-moves (plies) that are displayed in analysis in terminal |
| `max_plies_board`    | `3`      | The number of half-moves that are indicated through blink led sequences on the Millennium chess board. Maximum (due to hardware protocol limitations) is `3`. If more than one UCI engine is used for analysis, the results of the first engine are shown.|
| `ply_vis_delay`      | `80`     | The delay used went indicating move-sequences on the  Millennium chess board. Use a higher value (e.g. `160`) to slow down the speed of change. |
| `import_chesslink_position` | `true` | On `true` the current position on the Millennium chess board  is imported at start of `mchess.py`. On `false`, always the start position is used. |
| `computer_player_name` | `stockfish` | Name of the first computer UCI engine. It must correspond to the name of a json file in `mchess/engines/<computername>.json`. The first computer_player is the actual oponent in  human-computer games and is used for display of analysis on the Millennium board. Spelling (including case) must match engine filename _and_ `name` field in `<engine>.json`. [This is not really an optimal solution and will change.] |
| `computer_player2_name` | `""` | Name of optional second UCI engine, used for computer-computer games and as second, concurrent analysis engine. |
| `human_name` | `human` | Name of human player displayed in terminal. This will change (support for second name) |
| `active_agents` | `{ "human": ["chess_link", "terminal", "web"], "computer": ["stockfish", "lc0"]}` | Work in progress! A list of active agent modules. The agent-architecture is very flexible and allow adding arbitrary input and output hard- and software or interfaces to remote sites. |

### `chess_link_config.json`, configuration options for Millennium ChessLink hardware

This file configures the  Millennium chess board ChessLink hardware connection. This file is created during automatic hardware
detection at start of `mchess.py`.

| Field                | Default  | Description                                             |
| -------------------- | -------- | --------------------------------------------------------|
| `transport` | `chess_link_usb` | Name of the Python module to connect to the ChessLink hardware, currently supported are `chess_link_usb` or `chess_link_bluepy`. It's possible to add additional implementations (e.g. macOS or Windows Bluetooth) at a later time. |
| `address` | `""` | Bluetooth address or USB port name. |
| `orientation` | true | Orientation of the Millennium chess board. The orientation is detected and saved automatically as soon as the start position is setup on the Millennium board.
| `autodetect` | `true` | On `true`, automatic hardware detection of Millennium ChessLink is tried on each start of `mchess.py`, if the default connection does not work. Setting to `false` disables automatic hardware detection (e.g. if no board hardware is available) |
| `protocol_debug` | `false` | On `true` extensive logging of the hardware communication with the Millennium board is enabled for debugging purposes. |
| `btle_iface` | 1 | Linux Bluetooth LE interface number. If scanning continues to fail, it might help to use values from 0..2 for alternative tests. Not used for USB connections. |

### Json files in `mchess/engines`

Currently `mchess` supports up to two concurrent UCI chess engines. Each engine needs a configuration file `mchess/engines/<engine-name>.json`. On first start `mchess.py` automatically searches for stockfish, komodo and crafty.

The mandatory fields in `<engine-name>.json` are:

| Field                | Default  | Description                                             |
| -------------------- | -------- | --------------------------------------------------------|
| `name`               | e.g. `"stockfish"`     | Name of executable of the engine, e.g. `stockfish`. Unfortunately this name must be precisely equal to the name of the json file, and must be referenced in `preferences.json` as either `computer_player_name` or `computer_player2_name` and within `active_agents`. That is subject to improvement in the future. |
| `path` | e.g. `"/usr/local/bin/stockfish"` | Path to the engine executable. Windows users must either use `\\` or `/` in json files as path separators. |
| `active` | `true` | `mchess.py` currently uses only the first two active engines. If more engines are configured, the unused ones should be set to `false` |

Once the UCI engine is started for the first time, the UCI-options of the engine are enumerated and added to the `<engine-name>.json` config file. That allows further customization of each engine. Some commonly used options are:

| Field                | Default  | Description                                             |
| -------------------- | -------- | --------------------------------------------------------|
| `Threads`            | `1`      | Number of threads used for the engine, increase for higher engine performance. |
| `Hash` | `""` | Size of hash table, usually in MB. Increase for better performance |
| `MultiPV` | `1` | Increasing this shows more concurrent lines during analysis both on terminal and web client. A maximum of `4` is recommended, but not enforced. |
| `SyzygyPath` | `""` | Path to tablebase endgame databases. `mchess` outputs the number of tablebase references (TB) |

Warning: all customizations are reset, if an engine-update changes the available UCI-options. If a new engine version introduces
new UCI-options, all fields are reset to engine-defaults.

Additionally a file `<engine-name>-help.json` is auto-created, it contains descriptions for each UCI-option, and will be used in 
the future for an UCI-customization option.

## Architecture

```
                                +--------------------+
                                |      mchess.py     |   Start and connect agents
                                +--------------------+   agents represent player activities
                                         |     
                        +----------------+---------------+----------------------+  
                        |                |               |                      |
     +---------------------+  +--------------------+  +-------------------+ +--------------+
     | chess_link_agent.py |  | async_uci_agent.py |  | terminal_agent.py | | web_agent.py |
     +---------------------+  +--------------------+  +-------------------+ +--------------+
                        |            uci-engines         I/O hardware         multiple web
                        |            Stockfish,                               clients
                        |            Lc0 etc.                
 -  -  -  -  -  -  -  - | -  -  -  -  -  -  -  -  -  -  -  -
               +---------------+
               | chess_link.py |           Python 3 chess link library, can be
               +---------------+           reused for other projects without agents above
                  |         |
  +-------------------+  +----------------------+
  | chess_link_usb.py |  | chess_link_bluepy.py |
  +-------------------+  +----------------------+
         Chess Genius Exclusive board hardware
         via Chess Link
```

It whould be straight forward to include other agents at a later point.

## Troubleshooting

* Start with option `-v` to get more logging output:

```bash
python3 mchess.py -v
```

* Linux users: many distris require users to be be in group `DIALOUT` in order to access USB and serials.

```bash
usermod -aG dialout <username>
```

* ChessLink communication debug

Open `chess_link_config.json` and insert a line:

`"protocol_debug": true,`

like so:

```json
{
"protocol_debug": true,
"transport": "chess_link_bluepy",
"address": "xx:xx:xx:xx:xx:xx",
"btle_iface": 1,
"orientation": true,
"autodetect": true
}
```

This will show bit-level communication with the ChessLink board.

## History
* 2020-04-28: Work started on updating changes in module depencies (especially the async interface python-chess)

## Documentation

[API Documentation for chess_link.py](https://domschl.github.io/python-mchess/doc/build/html/index.html)

## Important external projects used by this project

* [python-chess](https://python-chess.readthedocs.io/en/latest/): a pure Python chess library
* [cm-chessboard](https://github.com/shaack/cm-chessboard): a chessboard rendered in SVG, coded in ES6. Views FEN, handles move input, animated, responsive, mobile friendly.
* [bluepy](https://github.com/IanHarvey/bluepy): Python interface to Bluetooth LE on Linux
* TBD

## Acknowledgements

* Thanks to Millennium GmbH for providing all information necessary for the implementation and for
  providing a ChessLink sample. See: [for more information](http://computerchess.de/#ChessLink) on ChessLink.
