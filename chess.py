import serial
import time


class MillenniumChess:
    def __init__(self, port):
        self.ser_port = serial.Serial(port, 38400, timeout=1)
        self.ser_port.dtr = 1

    def add_odd_par(self, b):
        byte = ord(b) & 127
        par = 1
        for _ in range(7):
            bit = byte & 1
            byte = byte >> 1
            par = par ^ bit
        if par == 1:
            byte = ord(b) & 127
            # byte = ord(b) | 128
        else:
            byte = ord(b) & 127
        return byte

    def hexd(self, digit):
        if digit < 10:
            return chr(ord('0')+digit)
        else:
            return chr(ord('A')-10+digit)

    def hex(self, num):
        d1 = num//16
        d2 = num % 16
        s = self.hexd(d1)+self.hexd(d2)
        print(" cnv<{} {}>".format(num, s))
        return s

    def write(self, bytes):
        gpar = 0
        for b in bytes:
            gpar = gpar ^ ord(b)
        bytes = bytes+self.hex(gpar)
        print("-> {}".format(bytes))
        for b in bytes:
            bo = self.add_odd_par(b)
            print("[>{} {}]".format(b, bo))
            self.ser_port.write(bo)

    def read(self, num):
        for _ in range(num):
            b = self.ser_port.read(1)
            print("[{} {}]".format(b, str(b)))

    def disconnect(self):
        self.ser_port.close()


if __name__ == '__main__':
    print("Starting!")
    port = '/dev/tty.MILLENNIUMCHESS-SerialP'
    board = MillenniumChess(port)
    board.write("V")

    # time.sleep(0.1)
    board.read(7)
    board.disconnect()
    print("closed.")
