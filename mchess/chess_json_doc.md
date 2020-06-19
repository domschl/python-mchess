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

The generator can decide, if variants are provided as uci- or san-formatted
arrays. Recipients will receive both formats from dispatcher.

## Board moves

### Move



```json
{
    "cmd": "move",
    "uci": "move-in-uci-format (e.g. e2-e4, e8-g8, e7-e8Q, 0000)",
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
    "state": "idle or busy or offline",
    "message": "optional message",
    "name": "Descriptive name",
    "authors": "authors in case of engine",
    "class": "agent class, e.g. engine or human",
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
    "cmd": "import_hardware_board_position",
    "from": "name-of-hardware-board_agent, e.g. 'ChessLinkAgent'",
    "actor": "name-of-agent-sending-this"
}
```
