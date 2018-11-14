// Mchess.js
import { COLOR, Chessboard } from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js"

var mchessSocket = new WebSocket("ws://" + window.location.host + "/ws");
var mainBoard = null;
var secBoard = null;

mchessSocket.onopen = function (event) {
}

mchessSocket.onmessage = function (event) {
    var msg = JSON.parse(event.data)
    if (msg.hasOwnProperty("fen")) {

        console.log(msg["fen"])
        if (mainBoard == null) {
            mainBoard = new Chessboard(document.getElementById("board1"),
                {
                    position: msg["fen"],
                    style: {
                        showCoordinates: true,
                        showBorder: true
                    },
                    sprite: { url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg" }
                });
        } else {
            mainBoard.setPosition(msg["fen"]);
        }
    } else if (msg.hasOwnProperty("info")) {
        console.log("INFO")
        if (msg.info.hasOwnProperty("variant")) {
            console.log(msg.info["variant"]);
            document.getElementById("info").innerHTML = msg.info.variant;
        }
    }

}