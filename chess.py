import serial


class MillenniumChess:
    def __init__(self, port):
        self.ser_port = serial.Serial(port, 38400, timeout=1)

    def add_odd_par(b):
        byte = b & 127
        par = 1
        for i in range(7):
            bit = byte >> 1
            byte = byte / 2
            par = par ^ bit
        if par == 1:
            byte = b | 128
        else:
            byte = b & 127
        return byte

    def write(bytes):
        gpar = 0
        for b in bytes:
            gpar = gpar ^ b

    def disconnect(self):
        self.ser_port.close()


if __name__ == '__main__':
    print("Staring!")
    port = '/dev/tty.Bluetooth-Incoming-Port'
    board = MillenniumChess(port)
    print("closed.")
