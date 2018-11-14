// Mchess.js

var mchessSocket = new WebSocket("ws://localhost:8001/ws");

mchessSocket.onopen = function (event) {
    mchessSocket.send("Hey, you!");
}

mchessSocket.onmessage = function (event) {
    console.log(event)
}