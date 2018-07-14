import serial
import serial.tools.list_ports
import time


class MillenniumChess:
    def __init__(self, port="", mode="USB"):
        self.replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}
        self.mode = mode
        if port == "":
            ports = self.port_search()
            if len(ports) > 0:
                print("Found {} Millennium boards.".format(len(ports)))
                port = ports[0]
                print("Autodetected Millennium board at: {}".format(port))
        if port and port != "":
            if self.port_check(port):
                try:
                    self.ser_port = serial.Serial(port, 38400)  # , timeout=1)
                    if self.mode == 'USB':
                        self.ser_port.dtr = 0
                    self.init = True
                except (OSError, serial.SerialException) as e:
                    print("Can't open port {}, {}".format(port, e))
                    self.init = False
            else:
                print("Invalid port {}".format(port))
                self.init = False
        else:
            print("No port found.")
            self.init = False

    def version_quick_check(self, port, verbose=True):
        try:
            if verbose is True:
                print("Testing port: {}".format(port))
            self.ser_port = serial.Serial(port, 38400)  # , timeout=1)
            if self.mode == 'USB':
                self.ser_port.dtr = 0
            self.init = True
            self.write("V")
            version = self.read(7)
            if len(version) != 7:
                self.ser_port.close()
                self.init = False
                if verbose is True:
                    print("Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                if verbose is True:
                    print("Unexpected reply {}".format(version))
                self.ser_port.close()
                self.init = False
                return None
            version = '{}.{}'.format(version[1:2], version[3:4])
            if verbose is True:
                print("Millenium {} at {}", version, port)
            self.ser_port.close()
            self.init = False
            return version
        except (OSError, serial.SerialException):
            pass
        self.ser_port.close()
        self.init = False
        return None

    def port_check(self, port, verbose=True):
        try:
            s = serial.Serial(port, 38400)  # , timeout=1)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            if verbose:
                print("Can't open port {}, {}".format(port, e))
            return False

    def port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.port_check(port, False):
                version = self.version_quick_check(port)
                if version != None:
                    print("Found: {}".format(version))
                    vports.append(port)
        return vports

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
        return s

    def write(self, msg):
        if self.init:
            try:
                self.ser_port.reset_input_buffer()
            except (Exception) as e:
                print("Failed to empty read-buffer: {}", e)
            gpar = 0
            for b in msg:
                gpar = gpar ^ ord(b)
            msg = msg+self.hex(gpar)
            print("-> {}".format(msg))
            bts = []
            for c in msg:
                bo = self.add_odd_par(c)
                bts.append(bo)
            try:
                n = self.ser_port.write(bts)
                self.ser_port.flush()
                print("Written: {}".format(n))
            except (Exception) as e:
                print("Failed to write {}: {}", msg, e)
        else:
            print("No open port for write")

    def read(self, num):
        rep = []
        if self.init:
            for _ in range(num):
                try:
                    b = chr(ord(self.ser_port.read()) & 127)
                    rep.append(b)
                except (Exception) as e:
                    print("Read error {}".format(e))
                    pass
        else:
            print("No open port for read")
        if len(rep) > 2:
            gpar = 0
            for b in rep[:-2]:
                gpar = gpar ^ ord(b)
            if rep[-2]+rep[-1] != self.hex(gpar):
                print("CRC error rep={} CRCs: {}!={}".format(rep,
                                                             rep[-2], self.hex(gpar)))
                return []
        return rep

    def disconnect(self):
        if self.init:
            self.ser_port.close()
            self.init = False


if __name__ == '__main__':
    print("Starting!")
    # port = '/dev/tty.MILLENNIUMCHESS-SerialP'
    port = '/dev/ttyUSB0'  # rfcomm1'
    # port = '/dev/rfcomm1'
    board = MillenniumChess()

    '''
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
    '''

    cmd = "V"
    board.write(cmd)
    board.read(7)

    cmd = "S"
    board.write(cmd)
    board.read(67)
    board.disconnect()
    print("closed.")
