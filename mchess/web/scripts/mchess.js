// Mchess.js
import {
    COLOR,
    Chessboard
} from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js"

// TODO: Remove hard coded port number (for live serve)
var mchessSocket = new WebSocket("ws://" + window.location.hostname + ":8001/ws");
var mainBoard = null;
var miniBoard1 = null;
var miniBoard2 = null;
var secBoard = null;

mchessSocket.onopen = function (event) { }

mchessSocket.onmessage = function (event) {
    var msg;
    try {
        msg = JSON.parse(event.data);
    } catch (err) {
        console.log('JSON error: ' + err.message);
        return;
    }
    if (msg.hasOwnProperty("fen")) {

        console.log(msg["fen"])
        if (mainBoard == null) {
            mainBoard = new Chessboard(document.getElementById("board1"), {
                position: msg["fen"],
                style: {
                    showCoordinates: true,
                    showBorder: true,
                },
                responsive: true,
                sprite: {
                    url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg"
                }
            });
            document.getElementById("board1").style.height = "250px";
            document.getElementById("board1").style.width = "250px";
        } else {
            mainBoard.setPosition(msg["fen"]);
        }

        if (miniBoard1 == null) {
            miniBoard1 = new Chessboard(document.getElementById("miniboard1"), {
                position: msg["fen"],
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
            miniBoard1.setPosition(msg["fen"]);
        }
        if (miniBoard2 == null) {
            miniBoard2 = new Chessboard(document.getElementById("miniboard2"), {
                position: msg["fen"],
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
            miniBoard2.setPosition(msg["fen"]);
        }
    } else if (msg.hasOwnProperty("info")) {
        console.log("INFO")
        if (msg.info.hasOwnProperty("variant")) {
            console.log(msg.info["variant"]);
            document.getElementById("miniinfo1").innerHTML = msg.info.variant;
        }
    }

}