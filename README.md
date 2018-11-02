# python-mchess

![Alpha status](https://img.shields.io/badge/Project%20status-Alpha-red.svg)
[![License](http://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](LICENSE)

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
`python-mchess` is written for Python 3.x

`python-mchess` board driver for Chess Link depends on `PySerial` and (Linux/Raspberry Pi only) `BluePy`

In order to use UCI engines with mchess, additionally `python-chess` is used.


```bash
pip3 install pyserial [bluepy] [python-chess]
```

Then clone the repository
```bash
git clone https://github.com/domschl/python-mchess
```

Now configure some engines:
```
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
Note: Windows users need to use paths with `\\` for proper json encoding.

Then in directory `mchess`, simply start from console:
```bash
python3 mchess.py
```

This will start chess agents for the chess board, automatically detecting board hardware via USB or BLuetooth LE (Linux, Raspberry PI only), and load the [first active] UCI engine (testet with Leela Chess Zero (Lc0) and Stockfish 9).

Note: Bluetooth LE hardware detection requires admin privileges for the one-time intial bluetooth scan. For first time start with Bluetooth LE support, use:
```bash
sudo python3 chess_mboard.py
```
Once the board is found, stop the program and restart without `sudo`. You might want to set ownership for `chess_link_config.json` to your user-account, since the file will be rewritten, if the detected board orientation is changed.

All engine descriptions in directory 'engines' will now contain the default-UCI options for each engine. Those can be edited e.g. to enable tablebases or other UCI options.

![Console mchess](https://raw.github.com/domschl/python-mchess/master/images/MchessAlpha.png)

## Usage

On start, the current position from Chess Genius Exclusive board is imported and displayed on the console.
Simply start making a move on the board, and the UCI engine will reply. During the time, the engine calculates,
the best current line is displayed on the board for up to 3 half-moves (see `preferences.json` to enable/disable this
feature).

## Architecture
```
                                +--------------------+
                                |   chess_mboard.py  |   Start and connect agents
                                +--------------------+
                                   |     |     |
                        +----------+     |     +---------+
                        |                |               |
         +---------------------+  +--------------+  +-------------------+
         | chess_link_agent.py |  | uci_agent.py |  | terminal_agent.py |   agents represent
         +---------------------+  +--------------+  +-------------------+   player activities 
                        |            uci-engines         I/O hardware
                        |            Stockfish,
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

It whould be straight forward to include other agents (e.g. pyqt5 GUI or web GUIs) at a later point.

## Documentation

[API Documentation for chess_link.py](https://domschl.github.io/python-mchess/doc/build/html/index.html)

## Acknowledgements

* Thanks to Millennium GmbH for providing all information necessary for the implementation and for
  providing a ChessLink sample. See: [for more information](http://computerchess.de/#ChessLink) on ChessLink.
