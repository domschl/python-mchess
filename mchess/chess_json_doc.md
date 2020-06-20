# Json commands for chess agent interaction

* Revision 0.1.0, 2020-June-18

This JSON protocol is used for agents communicating with the dispatcher
and for network-connections (e.g. websocket clients).

## Game modes

### New game

```json
{
    "cmd": "new_game",
    "mode": "optional-game-mode",
    "actor": "name-of-agent-sending-this"
}
```

### Game-mode (Human/computer vs human/computer)

```json
{
    "cmd": "game_mode",
    "mode": "human-human or human-computer or computer-human or computer_computer. computer can optionally be an engine-name",
    "level": "currently: optional computer think-time in ms",
    "actor": "name-of-agent-sending-this"
}
```

### Set computer play-strength level

```json
{
    "cmd": "set_level",
    "level": "currently: computer think-time in ms",
    "actor": "name-of-agent-sending-this"
}
```

### Quit, end program

```json
{
    "cmd": "quit",
    "actor": "name-of-agent-sending-this"
}
```



### Start analysis with chess engine

```json
{
    "cmd": "analyse",
    "actor": "name-of-agent-sending-this"
}
```

### Stop engine

```json
{
    "cmd": "stop",
    "actor": "name-of-agent-sending-this"
}
```

### Start engine (go)

```json
{
    "cmd": "go",
    "actor": "name-of-agent-sending-this"
}
```

### Turn (select side to move next, insert zero move, if necessary)

```json
{
    "cmd": "turn",
    "color": "white or black",
    "actor": "name-of-agent-sending-this"
}
```

### Import FEN position

```json
{
    "cmd": "import_fen",
    "fen": "FEN-encoded-position",
    "actor": "name-of-agent-sending-this"
}
```

### Import PGN game

```json
{
    "cmd": "import_pgn",
    "pgn": "pgn-text",
    "actor": "name-of-agent-sending-this"
}
```



## Game state information received by agents

### Update board display

This message is sent, if the board position changes. (New move, new game,
position imported etc.)

```json
{
    "cmd": "display_board",
    "fen": "FEN position",
    "pgn": "PGN game history",
    "attribs": {
        "unicode": true,
        "invert": false,
        "white": "name-of-white-player",
        "black": "name-of-black-player"
    }
}
```

### Engine information

Provide information while UCI chess computer engine calculates about
best variations and evaluations. This message is sent often.

```json
{
    "cmd": "current_move_info",
    "multipv_index": "index of variant: 1 is main variant",
    "score": "centi-pawn score or #2 mate announcement",
    "depth": "search depth (half moves)",
    "seldepth": "selective search depth (half moves)",
    "nps": "nodes per second",
    "tbhits": "table-base hits",
    "variant": [
        ["half-move-number", "uci-formatted moves"],
        ["half-move-number", "uci-formatted moves"],
    ],
    "san_variant": [
        ["full-move-number","white-move or ..","black-move"],
        ["full-move-number","white-move","black-move or empty"],
    ],
    "preview_fen_depth": "number of half moves for preview FEN",
    "preview_fen": "FEN <preview_fen_depth> half-moves in the future",
    "actor": "name-of-agent-sending-this"
}
```

The generator should provide only `"variant"` in uci format, a san-formatted variantformat
is added by the dispatcher for client-display use.

## Board moves

### Move

```json
{
    "cmd": "move",
    "uci": "move-in-uci-format (e.g. e2-e4, e8-g8, e7-e8Q, 0000)",
    "result": "empty, 1-0, 0-1, 1/2-1/2",
    "ponder": "t.b.d",
    "score": "optional (engine move) centi-pawn score or #2 mate announcement",
    "depth": "optional (engine move) search depth (half moves)",
    "seldepth": "optional (engine move) selective search depth (half moves)",
    "nps": "optional (engine move) nodes per second",
    "tbhits": "optional (engine move) table-base hits",
    "actor": "name-of-agent-sending-this"
}
```

### Take back move

```json
{
    "cmd": "move_back",
    "actor": "name-of-agent-sending-this"
}
```

### Move forward

```json
{
    "cmd": "move_forward",
    "actor": "name-of-agent-sending-this"
}
```

### Move to start of game

```json
{
    "cmd": "move_start",
    "actor": "name-of-agent-sending-this"
}
```

### Move to end of game

```json
{
    "cmd": "move_end",
    "actor": "name-of-agent-sending-this"
}
```

## Configuration messages

### update agent state

```json
{
    "cmd": "agent_state",
    "state": "idle or busy or offline or online",
    "message": "optional message",
    "name": "Descriptive name",
    "version": "Version information",
    "authors": "authors in case of engine",
    "class": "agent class, e.g. engine, board",
    "actor": "name-of-agent-sending-this"
}
```

### Text encoding

```json
{
    "cmd": "text_encoding",
    "unicode": true,
    "actor": "name-of-agent-sending-this"
}
```

### Chose depth of preview FEN

```json
{
    "cmd": "preview_fen_depth",
    "depth": "number-of-half-moves-for-preview-position",
    "actor": "name-of-agent-sending-this"
}
```

### Get engine list

Request list of engines

```json
{
    "cmd": "get_engine_list",
    "actor": "name-of-agent-sending-this"
}
```

### Engine list

List of all engines currently known, reply to `get_engine_list`.

```json
{
    "cmd": "engine_list",
    "actor": "name-of-agent-sending-this",
    "engines": {
        "name-of-engine-1" : {
            "name": "name-of-engine",
            "active": true,
            "options": {
                "Threads": 1,
                "MultiPV": 4,
                "SyzygyPath": "path-to-syzygy-endgame-database",
                "Ponder": false,
                "UCI_Elo": 1800,
                "Hash": 16
            }
        },
```
...
```json
        "name-of-engine-n": {
            "name": "name-of-engine-n",
            "active": true,
            "options": {
                "Threads": 1,
                "MultiPV": 4,
                "SyzygyPath": "path-to-syzygy-endgame-database",
                "Ponder": false,
                "UCI_Elo": 1800,
                "Hash": 16
            }
        }
    }
}
```

### Select player

```json
{
    "cmd": "select_player",
    "color": "white or black",
    "name": "human or name of uci engine",
    "actor": "name-of-agent-sending-this",
}
```

## Hardware board specific messages

### Hardware board orientation

```json
{
    "cmd": "turn_hardware_board",
    "actor": "name-of-agent-sending-this"
}
```

### Hardware board led mode

```json
{
    "cmd": "led_info",
    "plies": "number of plies to visualise with board leds (max 4)",
    "actor": "name-of-agent-sending-this"
}
```

### Fetch hardware board position

```json
{
    "cmd": "position_fetch",
    "from": "name-of-[hardware-]board-agent from which position should be fetched, e.g. 'ChessLinkAgent'",
    "actor": "name-of-agent-sending-this"
}
```

### Raw board position

```json
{
    "cmd": "raw_board_position",
    "fen": "unchecked-postion-on-hardware-board-for-debugging",
    "actor": "name-of-agent-sending-this"
}
```
