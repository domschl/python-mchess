import serial
import time


class MillenniumChess:
    def __init__(self, port):
        self.ser_port = serial.Serial(port, 38400)  # , timeout=1)
        self.ser_port.dtr = 0

    def add_odd_par(self, b):
        byte = ord(b) & 127
        par = 1
        for _ in range(7):
            bit = byte & 1
            byte = byte >> 1
            par = par ^ bit
        if par == 1:
            # byte = ord(b) & 127
            byte = ord(b) | 128
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

    def write(self, msg):
        gpar = 0
        for b in msg:
            gpar = gpar ^ ord(b)
        msg = msg+self.hex(gpar)
        print("-> {}".format(msg))
        bts = []
        for c in msg:
            bo = self.add_odd_par(c)
            bts.append(bo)
        n = self.ser_port.write(bts)
        self.ser_port.flush()
        print()
        print("Written: {}".format(n))

    def read(self, num):
        for _ in range(num):

            try:
                b = self.ser_port.read()
                print("[{}]".format(b))
            except:
                pass

    def disconnect(self):
        self.ser_port.close()


if __name__ == '__main__':
    print("Starting!")
    # port = '/dev/tty.MILLENNIUMCHESS-SerialP'
    port = '/dev/ttyUSB0'  # rfcomm1'
    board = MillenniumChess(port)

    cmd = "L50"
    for _ in range(81):
        cmd = cmd + "C4"
    board.write(cmd)
    # board.write("V")
    # time.sleep(0.1)
    board.read(3)
    # board.write("S")
    # board.read(10)

    time.sleep(5)
    cmd = "X"
    board.write(cmd)
    board.read(3)

    time.sleep(1)
    cmd = "V"
    board.write(cmd)
    board.read(3)

    board.disconnect()
    print("closed.")
