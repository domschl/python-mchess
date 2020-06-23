/*jshint esversion: 6 */
// Mchess.js
import {
    COLOR,
    MOVE_INPUT_MODE,
    INPUT_EVENT_TYPE,
    Chessboard
} from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js";
/*
import {
    Chart
} from "../node_modules/chart.js/dist/Chart.js"
*/
//var Chart = require("../node_modules/chart.js/dist/Chart.js")

var mainBoard = null;
var miniBoard1 = null;
var miniBoard2 = null;
var VariantInfo = null;
var EngineStates = null;
var engines = {};
var FenRef = {};
var StatHeader = {};
var ValidMoves = [];
var GameStats = {};
var id = null;

var oldFen = null;

wsConnect("ws://" + window.location.host + "/ws");

var cmds = {
    'agent_state': agent_state,
    'display_board': display_board,
    'current_move_info': current_move_info,
    'engine_list': engine_list,
    'move': set_move,
    'valid_moves': set_valid_moves,
    'game_stats': set_game_stats
}

var mchessSocket;
function wsConnect(address) {
    mchessSocket = new WebSocket(address);
    console.log(`Socket: ${mchessSocket}`);
    mchessSocket.onopen = function (event) {
        document.getElementById("connect-state").style.color = "#58A4B0";
        document.getElementById("connect-text").innerText = "connected";
        document.getElementById("")

        document.getElementById("m-new").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'new_game',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-new").blur();
        }, false);
        document.getElementById("m-bb").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'move_start',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-bb").blur();
        }, false);
        document.getElementById("m-bw").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'move_back',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-bw").blur();
        }, false);
        document.getElementById("m-st").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'stop',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-st").blur();
        }, false);
        document.getElementById("m-fw").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'move_forward',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-fw").blur();
        }, false);
        document.getElementById("m-ff").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'move_end',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-ff").blur();
        }, false);
        document.getElementById("m-analyse").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'analyse',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-analyse").blur();
        }, false);
        document.getElementById("m-import").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'position_fetch',
                'from': 'ChessLinkAgent',
                'actor': 'WebAgent'
            }));
            document.getElementById("m-import").blur();
        }, false);
        document.getElementById("m-send").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'cmd': 'import_fen', 'fen': document.getElementById("m-edit").value,
                'actor': 'WebAgent'
            }));
            document.getElementById("m-send").blur();
        }, false);
        document.getElementById("whiteplayer").addEventListener("change", function (event) {
            var pl = document.getElementById("whiteplayer");
            var player = String(pl.options[pl.selectedIndex].value);
            console.log('wplayer: '+player+" selected.")
            mchessSocket.send(JSON.stringify({
                'cmd': 'select_player',
                'color': 'white',
                'name': player,
                'actor': 'WebAgent'
            }));
        }, false);
        document.getElementById("blackplayer").addEventListener("change", function (event) {
            var pl = document.getElementById("blackplayer");
            var player = pl.options[pl.selectedIndex].value;
            console.log('bplayer: '+player+" selected.")
            mchessSocket.send(JSON.stringify({
                'cmd': 'select_player',
                'color': 'black',
                'name': player,
                'actor': 'WebAgent'
            }));
        }, false);
    }
    mchessSocket.onclose = function () {
        // Try to reconnect in 1 seconds
        document.getElementById("connect-state").style.color = "red";
        document.getElementById("connect-text").innerText = "disconnected";
        document.getElementById("chesslink-state").style.color = "red";
        document.getElementById("engine1-state").style.color = "red";
        document.getElementById("engine2-state").style.color = "red";
        mchessSocket = null;
        console.log(`Socket close: ${mchessSocket}`);
        ValidMoves=[];
        setTimeout(function () {
            wsConnect(address)
        }, 1000);dfgdfghyyhyh
    };
    mchessSocket.onmessage = function (event) {
        var msg;
        try {
            msg = JSON.parse(event.data);
        } catch (err) {
            console.log('JSON error: ' + err.message);
            return;
        }
        // console.log("got message: ")
        // console.log(msg)
        if (!msg.hasOwnProperty("cmd")) {
            console.log("received and ignored old-style message");
            console.log(msg);
        } else {
            if (!cmds.hasOwnProperty(msg['cmd'])) {
                console.log("cmd "+msg['cmd']+" is not yet implemented, ignored.");
                console.log(msg);
            } else {
                cmds[msg['cmd']](msg);
            }
        }

 
    }
}

function agent_state(msg) {
    console.log('agent_state msg: ' + msg['actor'] + ' ' + msg['state'] + ' ' + msg['message'])
    if (msg['actor'] == 'ChessLinkAgent') {
        if (msg['state'] == 'online') {
            document.getElementById("chesslink-state").style.color = "#58A4B0";
        } else {
            document.getElementById("chesslink-state").style.color = "red";
        }
    }
    if (msg['class']=='engine') {
        if (EngineStates==null) EngineStates={};
        if (!(msg['actor'] in EngineStates)) {
            id=Object.keys(EngineStates).length;
            EngineStates[msg['actor']]=id;
            //console.log(id);
            if (id==0) document.getElementById("engine1-name").innerHTML = msg['name'];
            else document.getElementById("engine2-name").innerHTML = msg['name'];
        }
        id=EngineStates[msg['actor']]
        if (id==0) {
            if (msg['state']=='busy') {
                document.getElementById("engine1-state").style.color = "#D8DBE2";
                document.getElementById("mb1-a").style.backgroundColor = "#D8DBE2";
            } else { 
                document.getElementById("engine1-state").style.color = "#58A4B0";
                document.getElementById("mb1-a").style.backgroundColor = "#58A4B0";
            }
        } else {
            if (msg['state']=='busy') {
                document.getElementById("engine2-state").style.color = "#D8DBE2";
                document.getElementById("mb2-a").style.backgroundColor = "#D8DBE2";
            } else { 
                document.getElementById("engine2-state").style.color = "#58A4B0";
                document.getElementById("mb2-a").style.backgroundColor = "#58A4B0";
            }
        }
    }
}

function availablePlayers() {
    var wHtml="<option class=\"panel-header\" value=\"human\">human</option>";
    for (var engine in engines) {
        wHtml = wHtml+"<option class=\"panel-header\" value=\""+engine+"\">"+engine+"</option>";
    }
    var bHtml="<option class=\"panel-header\" value=\"human\">human</option>"
    for (var engine in engines) {
        bHtml = bHtml+"<option class=\"panel-header\" value=\""+engine+"\">"+engine+"</option>";
    }
    document.getElementById("whiteplayer").innerHTML = wHtml;
    document.getElementById("blackplayer").innerHTML = bHtml;
}

function display_board(msg) {
    if (msg.hasOwnProperty("fen") && msg.hasOwnProperty("attribs") && msg.hasOwnProperty("pgn")) {
        console.log("got board position.");
        console.log(msg.pgn)
        console.log(msg.fen)
        if (msg.fen==oldFen) {
            console.log("position did not change, ignoring FEN update");
            return;
        }
        oldFen=msg.fen;
        if (mainBoard == null) {
            mainBoard = new Chessboard(document.getElementById("board1"), {
                position: msg.fen,
                style: {
                    showCoordinates: true,
                    showBorder: true,
                },
                responsive: true,
                moveInputMode: MOVE_INPUT_MODE.dragPiece,
                sprite: {
                    url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg"
                }
            });
            var brd = document.getElementsByClassName("board");
            document.getElementById("board1").style.height = "260px";
            document.getElementById("board1").style.width = "260px";
            console.log(brd[0].style.width);
            //document.getElementById("ph1").style.width = brd[0].style.width;
            mainBoard.enableMoveInput(chessMainboardInputHandler)
        } else {
            mainBoard.setPosition(msg.fen);
        }
        availablePlayers();
        var pi = msg.pgn.search("\n\n");
        var pgn = msg.pgn;
        if (pi != -1) {
            pgn = msg.pgn.substring(pi);
        }
        // pgn = pgn.replace(" *", "");
        pgn = pgn.replace(" ", "&nbsp;")
        var regex = /([0-9]+\.)/g;
        pgn = pgn.replace(regex, " <span class=\"movenrb\"> $1</span>")
        document.getElementById("mainmoves").innerHTML = pgn;

        if (miniBoard1 == null) {
            miniBoard1 = new Chessboard(document.getElementById("miniboard1"), {
                position: msg.fen,
                style: {
                    showCoordinates: true,
                    showBorder: true,
                },
                responsive: true,
                sprite: {
                    url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg"
                }
            });
            document.getElementById("miniboard1").style.height = "120px";
            document.getElementById("miniboard1").style.width = "120px";
        } else {
            miniBoard1.setPosition(msg.fen);
        }
        document.getElementById("miniinfo1").innerHTML=""
        document.getElementById("ph21").innerHTML=""
        if (miniBoard2 == null) {
            miniBoard2 = new Chessboard(document.getElementById("miniboard2"), {
                position: msg.fen,
                style: {
                    showCoordinates: true,
                    showBorder: true,
                },
                responsive: true,
                sprite: {
                    url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg"
                }
            });
            document.getElementById("miniboard2").style.height = "120px";
            document.getElementById("miniboard2").style.width = "120px";
        } else {
            miniBoard2.setPosition(msg.fen);
        }
        document.getElementById("miniinfo2").innerHTML=""
        document.getElementById("ph31").innerHTML=""
    }
}

function chessMainboardInputHandler(event) {
    console.log(event)
    switch (event.type) {
        case INPUT_EVENT_TYPE.moveStart:
            for (var mv in ValidMoves) {
                if (String(ValidMoves[mv].substring(0,2))==String(event.square)) {
                    console.log(`moveStart: ${event.square}`);
                    return true;
                }
            }
            console.log("invalid all")
            return false;
        case INPUT_EVENT_TYPE.moveDone:
            for (var mv in ValidMoves) {
                if (ValidMoves[mv]==event.squareFrom+event.squareTo) 
                {
                    console.log(`moveDone: ${event.squareFrom}-${event.squareTo}`);
                    console.log(`Socket: ${mchessSocket}`);
                    if (mchessSocket==null) {
                        console.log("Error: Cannot send move, undoing!");
                        return false;
                    }
                    mchessSocket.send(JSON.stringify({
                        'cmd': 'move',
                        'uci': ValidMoves[mv],
                        'actor': 'WebAgent'
                    }));
                    ValidMoves=[];
                    return true;
                }
            }
            console.log(`invalid move: ${event.squareFrom}-${event.squareTo}`);
            return false;
        case INPUT_EVENT_TYPE.moveCanceled:
            console.log(`moveCanceled`)
    }
}

function current_move_info(msg) {
    if (VariantInfo == null) {
        VariantInfo = {};
    }
    console.log(msg)
    if (msg.hasOwnProperty("san_variant")) {
        //console.log("V");
        var actor = msg.actor;
        var id = msg.multipv_index;
        if (!(actor in VariantInfo)) {
            VariantInfo[actor] = {}
        }
        if (id == 1) FenRef[actor] = msg["preview_fen"];
        var hd = ""
        if ("nps" in msg) {
            hd += " | Nps: " + msg.nps;
        }
        if (id == 1 && "score" in msg) {
            hd += " | Score: " + msg.score;
        }
        if ("depth" in msg) {
            hd += " | Depth: " + msg.depth;
            if ("seldepth" in msg) {
                hd += "/" + msg.seldepth;
            }
        }
        if ("tbhits" in msg) {
            hd += " | TbHits: " + msg["tbhits"];
        }
        hd += " |";
        StatHeader[actor] = hd;
        var htmlpgn = "<div class=\"variant\"><span class=\"leadt\">";
        if (msg.score!="") htmlpgn+="[" + msg.score + "]";
        else htmlpgn+="&nbsp;&nbsp;&nbsp;&nbsp;";
        htmlpgn+="</span>&nbsp;&nbsp;";
        var first = true;
        for (var mvi in msg.san_variant) {
            if (mvi == "fen") continue;
            var mv = msg.san_variant[mvi];
            if (mvi != 0) htmlpgn += "&nbsp;";
            var mv1 = mv[1].replace('-', '‑'); // make dash non-breaking
            var mv2 = "";
            if (mv.length > 2) {
                var mv2 = mv[2].replace('-', '‑');
            }
            if (first) {
                if (mv1 == '..')
                    htmlpgn += "<span class=\"movenr\">" + mv[0] + ".</span>&nbsp;" + mv1 + "&nbsp;<span class=\"mainmove\">" + mv2 + "</span> ";
                else
                    htmlpgn += "<span class=\"movenr\">" + mv[0] + ".</span>&nbsp;<span class=\"mainmove\">" + mv1 + "</span>&nbsp;" + mv2 + " ";
                first = false;
            } else {
                htmlpgn += "<span class=\"movenr\">" + mv[0] + ".</span>&nbsp;" + mv1 + "&nbsp;" + mv2 + " ";
            }
        }
        htmlpgn += "</div>";
        VariantInfo[actor][id] = htmlpgn

        var n = 0;
        for (var actorName in VariantInfo) {
            var ai = VariantInfo[actorName];
            var htmlpi = "";
            for (var j in ai) {
                htmlpi += ai[j];
            }
            if (n == 0) {
                document.getElementById("miniinfo1").innerHTML = htmlpi;
                document.getElementById("ph2").innerText = actorName;
                if (FenRef.hasOwnProperty(actorName)) {
                    miniBoard1.setPosition(FenRef[actorName], false);
                }
                document.getElementById("ph21").innerText = StatHeader[actorName];
            }
            if (n == 1) {
                document.getElementById("miniinfo2").innerHTML = htmlpi;
                document.getElementById("ph3").innerText = actorName;
                if (FenRef.hasOwnProperty(actorName)) {
                    miniBoard2.setPosition(FenRef[actorName], false);
                }
                document.getElementById("ph31").innerText = StatHeader[actorName];
            }
            n += 1;
        }
    }
}

function engine_list(msg) {
    // console.log(msg);
    for (var engine in msg["engines"]) {
        console.log("Received info for engine "+engine);
    }
    engines = msg["engines"];
    availablePlayers();
}

function set_move(msg) {
    console.log("Ignoring move-cmd");
}

function set_valid_moves(msg) {
    ValidMoves=msg.valid_moves;
}

function set_game_stats(stats_msg) {
    console.log("Received stats msg");
    var stats = stats_msg['stats'];
    var lbls = [];
    var dsb=[];
    var dsw=[];
    for (var i=0; i<stats.length; i++) {
        if (stats[i].hasOwnProperty("score")) {
            if (stats[i].color=="WHITE") {
                lbls.push(`${stats[i].move_number} (W)`);
                dsw.push(stats[i].score);
            } else {
                lbls.push(`${stats[i].move_number} (B)`);
                dsb.push(stats[i].score);
            }
        }
    }
    console.log(`lbls: ${lbls}, dsw: ${dsw}, dsb: ${dsb}`);
    var ctx = document.getElementById('stats');
    var myLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: lbls,
            datasets: [
                { 
                    label: "White score",
                    backgroundColor: "#2E3532",
                    borderColor: "#D8DBE2", 
                    cubicInterpolationMode: "monotone",
                    lineTension: 0.4,
                    fill: false,
                    borderWidth: 1,
                    data: dsw
                },
                { 
                    label: "Black score",
                    backgroundColor: "#2E3532",
                    borderColor: "#58A4B0",
                    borderWidth: 1,
                    lineTension: 0.4,
                    fill: false,
                    cubicInterpolationMode: "monotone",
                    data: dsb 
                }
            ]
        },
        options: {
            responsive: true,
            legend: {
                labels: {
                    fontColor: "#D8DBE2",
                    fontSize: 11
                }
            },
            scales: {
                xAxes: [{
                    display: true,
                    ticks: {
                        fontSize: 10,
                        fontColor: "#D8DBE2"
                    }
                }],
                yAxes: [{
                    display: true,
                    ticks: {
                        fontSize: 10,
                        fontColor: "#D8DBE2"
                    }
                }]
    
            }
        }
    });    
}
