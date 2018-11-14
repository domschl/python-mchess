// Mchess.js
import { COLOR, Chessboard } from "../node_modules/cm-chessboard/src/cm-chessboard/Chessboard.js"

var mchessSocket = new WebSocket("ws://ncc1701.fritz.box:8001/ws");
var mainBoard = null;

mchessSocket.onopen = function (event) {
    // mchessSocket.send("Hey, you!");
}

mchessSocket.onmessage = function (event) {
    var msg = JSON.parse(event.data)
    console.log(msg["fen"])
    if (mainBoard == null) {
        console.log("New board.")
        mainBoard = new Chessboard(document.getElementById("board1"),
            {
                position: msg["fen"],
                sprite: { url: "node_modules/cm-chessboard/assets/images/chessboard-sprite.svg" }
            });
    } else {
        console.log("upd:" + msg["fen"])
        mainBoard.setPosition(msg["fen"]);
    }

}