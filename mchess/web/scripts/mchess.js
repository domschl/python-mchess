// Mchess.js
import {
    COLOR,
    Chessboard
} from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js"

var mchessSocket = new WebSocket("ws://" + window.location.host + "/ws");
var mainBoard = null;
var miniBoard1 = null;
var miniBoard2 = null;
var VariantInfo = null;
var FenRef = {};

mchessSocket.onopen = function (event) { }

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
        if (VariantInfo != null) {
            for (var a in VariantInfo) {
                VariantInfo[a] = {}
                FenRef[a] = msg.fen;
            }
        }
        document.getElementById("miniinfo1").innerHTML = "";
        document.getElementById("miniinfo2").innerHTML = "";
        var title = msg.attribs.white_name + " - " + msg.attribs.black_name;
        console.log(msg.fen)
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
    } else if (msg.hasOwnProperty("info")) {
        if (VariantInfo == null) {
            VariantInfo = {};
        }
        if (msg.info.hasOwnProperty("variant")) {
            console.log("V");
            var actor = msg.info.actor;
            var id = msg.info.multipv_ind;
            if (!(actor in VariantInfo)) {
                VariantInfo[actor] = {}
            }
            if (id == 1) FenRef[actor] = msg["fenref"];
            var htmlpgn = "<div class=\"variant\">[" + msg.info.score + "] &nbsp;";
            for (var mvi in msg.info.variant) {
                if (mvi == "fen") continue;
                var mv = msg.info.variant[mvi];
                if (mvi != 0) htmlpgn += "&nbsp;";
                var mv1 = mv[1].replace('-', '‑'); // make dash non-breaking
                var mv2 = "";
                if (mv.length > 2) {
                    var mv2 = mv[2].replace('-', '‑');
                }
                htmlpgn += "<span class=\"movenr\">" + mv[0] + ".</span>&nbsp;" + mv1 + "&nbsp;" + mv2 + " ";
            }
            htmlpgn += "</div>";
            VariantInfo[actor][id] = htmlpgn

            var n = 0;
            for (var i in VariantInfo) {
                var ai = VariantInfo[i];
                var htmlpi = "";
                for (var j in ai) {
                    htmlpi += ai[j];
                }
                if (n == 0) {
                    document.getElementById("miniinfo1").innerHTML = htmlpi;
                    document.getElementById("ph2").innerText = i;
                    miniBoard1.setPosition(FenRef[i], false);
                }
                if (n == 1) {
                    document.getElementById("miniinfo2").innerHTML = htmlpi;
                    document.getElementById("ph3").innerText = i;
                    miniBoard2.setPosition(FenRef[i], false);
                }
                n += 1;
            }
        }
    }

}