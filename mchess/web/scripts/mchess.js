// Mchess.js
import { COLOR, Chessboard } from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js"

var mchessSocket = new WebSocket("ws://" + window.location.host + "/ws");
var mainBoard = null;

mchessSocket.onopen = function (event) {
}

mchessSocket.onmessage = function (event) {
    var msg = JSON.parse(event.data)
    console.log(msg["fen"])
    if (mainBoard == null) {
        mainBoard = new Chessboard(document.getElementById("board1"),
            {
                position: msg["fen"],
                sprite: { url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg" }
            });
    } else {
        mainBoard.setPosition(msg["fen"]);
    }

}