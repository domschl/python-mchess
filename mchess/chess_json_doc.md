# Json commands for chess agent interaction

* Revision 0.1.0, 2020-June-18

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

### Set computer level

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

* Black/white are redundant? (in pgn)

```json
{
    "cmd": "display_board",
    "fen": "FEN position",
    "pgn": "PGN game history",
    "white": "name-of-white-player",
    "black": "name-of-black-player",
    "actor": "name-of-agent-sending-this"
}
```

### Engine information

```json
{
    "cmd": "current_move_info",
    "actor": "name-of-agent-sending-this"
}
```



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

## Hardware board specific messages

### Hardware board orientation

### Hardware board led mode

### Fetch hardware board position