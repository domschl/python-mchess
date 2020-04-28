/*jshint esversion: 6 */
// Mchess.js
import {
    COLOR,
    Chessboard
} from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js";


var mainBoard = null;
var miniBoard1 = null;
var miniBoard2 = null;
var VariantInfo = null;
var FenRef = {};
var StatHeader = {};

var oldFen = null;

wsConnect("ws://" + window.location.host + "/ws");

function wsConnect(address) {
    var mchessSocket = new WebSocket(address);
    mchessSocket.onopen = function (event) {
        document.getElementById("connect-state").style.color = "#58A4B0";
        document.getElementById("connect-text").innerText = "connected";
        document.getElementById("")

        document.getElementById("m-new").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'new game': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-new").blur();
        }, false);
        document.getElementById("m-bb").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'fast-back': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-bb").blur();
        }, false);
        document.getElementById("m-bw").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'back': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-ba").blur();
        }, false);
        document.getElementById("m-st").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'stop': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-st").blur();
        }, false);
        document.getElementById("m-fw").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'forward': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-fw").blur();
        }, false);
        document.getElementById("m-ff").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'fast-forward': '',
                actor: 'WebAgent'
            }));
            document.getElementById("m-ff").blur();
        }, false);
        document.getElementById("m-import").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'position_fetch': 'ChessLinkAgent',
                actor: 'WebAgent'
            }));
            document.getElementById("m-import").blur();
        }, false);
        document.getElementById("m-send").addEventListener("click", function (event) {
            mchessSocket.send(JSON.stringify({
                'fen_setup': document.getElementById("m-edit").value,
                actor: 'WebAgent'
            }));
            document.getElementById("m-send").blur();
        }, false);
    }
    mchessSocket.onclose = function () {
        // Try to reconnect in 1 seconds
        document.getElementById("connect-state").style.color = "red";
        document.getElementById("connect-text").innerText = "disconnected";
        mchessSocket = null;
        setTimeout(function () {
            wsConnect(address)
        }, 1000);
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
        if (msg.hasOwnProperty("fen") && msg.hasOwnProperty("attribs") && msg.hasOwnProperty("pgn")) {
            console.log("got board position.");
            console.log(msg.pgn)
            /*
            if (VariantInfo != null) {
                for (var a in VariantInfo) {
                    VariantInfo[a] = {}
                    FenRef[a] = msg.fen;
                }
            }
            StatHeader = {};
            document.getElementById("miniinfo1").innerHTML = "";
            document.getElementById("miniinfo2").innerHTML = "";
            document.getElementById("ph21").innerHTML = "";
            document.getElementById("ph31").innerHTML = "";
            */
            var title = msg.attribs.white_name + " - " + msg.attribs.black_name;
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
                    sprite: {
                        url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg"
                    }
                });
                var brd = document.getElementsByClassName("board");
                document.getElementById("board1").style.height = "260px";
                document.getElementById("board1").style.width = "260px";
                console.log(brd[0].style.width);
                //document.getElementById("ph1").style.width = brd[0].style.width;
            } else {
                mainBoard.setPosition(msg.fen);
            }
            document.getElementById("ph1").innerText = title;
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
        } else if (msg.hasOwnProperty("info")) {
            if (VariantInfo == null) {
                VariantInfo = {};
            }
            if (msg.info.hasOwnProperty("variant")) {
                //console.log("V");
                var actor = msg.info.actor;
                var id = msg.info.multipv_ind;
                if (!(actor in VariantInfo)) {
                    VariantInfo[actor] = {}
                }
                if (id == 1) FenRef[actor] = msg["fenref"];
                var hd = ""
                if ("nps" in msg.info) {
                    hd += " | Nps: " + msg.info.nps;
                }
                if (id == 1 && "score" in msg.info) {
                    hd += " | Score: " + msg.info.score;
                }
                if ("depth" in msg.info) {
                    hd += " | Depth: " + msg.info.depth;
                    if ("seldepth" in msg.info) {
                        hd += "/" + msg.info.seldepth;
                    }
                }
                if ("tbhits" in msg.info) {
                    hd += " | TbHits: " + msg.info["tbhits"];
                }
                hd += " |";
                StatHeader[actor] = hd;
                var htmlpgn = "<div class=\"variant\"><span class=\"leadt\">";
                if (msg.info.score!="") htmlpgn+="[" + msg.info.score + "]";
                else htmlpgn+="&nbsp;&nbsp;&nbsp;&nbsp;";
                htmlpgn+="</span>&nbsp;&nbsp;";
                var first = true;
                for (var mvi in msg.info.variant) {
                    if (mvi == "fen") continue;
                    var mv = msg.info.variant[mvi];
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
                        miniBoard1.setPosition(FenRef[actorName], false);
                        document.getElementById("ph21").innerText = StatHeader[actorName];
                    }
                    if (n == 1) {
                        document.getElementById("miniinfo2").innerHTML = htmlpi;
                        document.getElementById("ph3").innerText = actorName;
                        miniBoard2.setPosition(FenRef[actorName], false);
                        document.getElementById("ph31").innerText = StatHeader[actorName];
                    }
                    n += 1;
                }
            }
        } else if (msg.hasOwnProperty("agent-state")) {
            console.log('agent-state msg: ' + msg['actor'] + ' ' + msg['agent-state'] + ' ' + msg['message'])
            if (msg['actor'] == 'ChessLinkAgent') {
                if (msg['agent-state'] == 'online') {
                    document.getElementById("chesslink-state").style.color = "#58A4B0";
                } else {
                    document.getElementById("chesslink-state").style.color = "red";
                }
            }
        }
    }
}