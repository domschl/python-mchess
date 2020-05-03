# Mchess todos

## Bugs and testing

- [ ] Handle inline TODOs

## Web

- [ ] Javascript mess cleanup
- [ ] Move input via chess.js integration
- [ ] Game state console (save/load PGN, modes)
- [ ] Log monitor
- [ ] Debug console
- [ ] Stats (Charts.js)
- [ ] Manual analysis board
- [ ] Moves clickable (variants, analysis-board)
- [ ] select depth for analysis-boards (move-sequences?)
- [ ] Turn board
- [ ] Turn eboard
- [ ] proper PWA boiler plate ('progressive web app')

## GUI

- [ ] TkInter tests

## Agents and main

- [ ] PGN-Libraries and ECO handling
- [ ] Data import module

## Performance

- [ ] General latency tests
- [ ] ChessLink latency and general event-queue latency tests
- [ ] Raspi event queue performance tests

## Game mode handling (and Web GUI)

- [ ] Consistent game mode handling
- [ ] Save PGN on exist and reload (fitting) history on restart
- [ ] Dropboxes for oponents
- [ ] Analysis buttons
- [ ] State machine review

## Features and longer-term stuff (post first beta)

- [ ] Local tournaments
- [ ] more complex multi-agent topologies (e.g. two web agents with different players,
      remote connections between mchess instances, distributed tournaments) c.f. JSON-Prot.
- [ ] MQTT agent
- [ ] Mac/Windows bluetooth support for ChessLink
- [ ] Elo calc
- [ ] (PGN-)Library agent
- [ ] Lichess eval (e.g. https://github.com/cyanfish/python-lichess)
- [ ] Checkout PyInstaller <https://pyinstaller.readthedocs.io/en/stable/operating-mode.html>
- [ ] Define proper agent JSON protocol (Net/JSON-UCI)
- [ ] Unit-tests, Travis
- [ ] PyPI publication

## Done

### ChessLink fixes and enhancements

- [x] Handle USB-reconnect
- [x] Handle Bluetooth-reconnect
- [x] Sync agent states (CL and others) to GUI-clients
- [x] Select look-ahead engine for LED display
- [x] Verify consistent mutex usage

- [x] Current UCI API of python-chess is deprecated. Change to ASYNC engine api.
- [x] Clear analysis of engines on new game or new pos
- [x] Analyse python-chess corruptions (thread race-conditions?)
- [x] Filter duplicate UCI depth messages (esp. lc0)
- [x] Bluetooth LE sometimes fails to connect. Retry strategy does not work (other than restarting)
- [x] Better handling of display of check mate situations with Millennium Board (led king animation?)
