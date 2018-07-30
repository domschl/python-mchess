import serial
import serial.tools.list_ports
import time
import threading
import chess
import chess.uci
import os


class MillenniumChess:
    def __init__(self, port="", mode="USB", verbose=False):
        self.replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.mode = mode
        self.verbose = verbose
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
                    self.port = port
                except (OSError, serial.SerialException) as e:
                    print("Can't open port {}, {}".format(port, e))
                    self.init = False
            else:
                print("Invalid port {}".format(port))
                self.init = False
        else:
            print("No port found.")
            self.init = False

    def version_quick_check(self, port):
        try:
            if self.verbose is True:
                print("Testing port: {}".format(port))
            self.ser_port = serial.Serial(port, 38400, timeout=1)
            if self.mode == 'USB':
                self.ser_port.dtr = 0
            self.init = True
            self.write("V")
            version = self.read(7)
            if len(version) != 7:
                self.ser_port.close()
                self.init = False
                if self.verbose is True:
                    print("Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                if self.verbose is True:
                    print("Unexpected reply {}".format(version))
                self.ser_port.close()
                self.init = False
                return None
            version = '{}.{}'.format(version[1:2], version[3:4])
            if self.verbose is True:
                print("Millenium {} at {}", version, port)
            self.ser_port.close()
            self.init = False
            return version
        except (OSError, serial.SerialException):
            pass
        self.ser_port.close()
        self.init = False
        return None

    def port_check(self, port):
        # if port[:9] == "/dev/ttyS" or 'Incoming' in port:
        #    return False
        try:
            if self.verbose:
                print("Testing port: {}".format(port))

            s = serial.Serial(port, 38400)  # , timeout=1)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            if self.verbose:
                print("Can't open port {}, {}".format(port, e))
            return False

    def port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.port_check(port):
                verb = self.verbose
                self.verbose = False
                version = self.version_quick_check(port)
                self.verbose = verb
                if version != None:
                    if self.verbose:
                        print("Found board at: {}".format(port))
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
                if self.verbose:
                    print("Failed to empty read-buffer: {}", e)
            gpar = 0
            for b in msg:
                gpar = gpar ^ ord(b)
            msg = msg+self.hex(gpar)
            bts = []
            for c in msg:
                bo = self.add_odd_par(c)
                bts.append(bo)
            try:
                n = self.ser_port.write(bts)
                self.ser_port.flush()
            except (Exception) as e:
                if self.verbose:
                    print("Failed to write {}: {}", msg, e)
        else:
            if self.verbose:
                print("No open port for write")

    def read(self, num):
        rep = []
        if self.init:
            for _ in range(num):
                try:
                    b = chr(ord(self.ser_port.read()) & 127)
                    rep.append(b)
                except (Exception) as e:
                    if self.verbose:
                        print("Read error {}".format(e))
                    break
        else:
            if self.verbose:
                print("No open port for read")
        if len(rep) > 2:
            gpar = 0
            for b in rep[:-2]:
                gpar = gpar ^ ord(b)
            if rep[-2]+rep[-1] != self.hex(gpar):
                if self.verbose:
                    print("CRC error rep={} CRCs: {}!={}".format(rep,
                                                                 rep[-2], self.hex(gpar)))
                return []
        return rep

    def get_version(self):
        version = ""
        self.write("V")
        version = self.read(7)
        if len(version) != 7:
            return ""
        if version[0] != 'v':
            return ""
        version = '{}.{}'.format(version[1]+version[2], version[3]+version[4])
        return version

    def get_position_raw(self):
        cmd = "S"
        self.write(cmd)
        rph = self.read(67)
        if len(rph) != 67:
            return ""
        if rph[0] != 's':
            return ""
        return rph[1:65]

    def get_position(self):
        rp = self.get_position_raw()
        position = [[0 for x in range(8)] for y in range(8)]
        if len(rp) == 64:
            for y in range(8):
                for x in range(8):
                    c = rp[7-x+y*8]
                    i = self.figrep['ascii'].find(c)
                    if i == -1:
                        print("Invalid char in raw position: {}".format(c))
                        return None
                    else:
                        f = self.figrep['int'][i]
                        position[y][x] = f
        else:
            print("Error in board postion, received {}".format(len(rp)))
            return None
        return position

    def set_reference(self):
        self.refpos = self.get_position()

    def show_delta(self, pos):
        dpos = [[0 for x in range(8)] for y in range(8)]
        for y in range(8):
            for x in range(8):
                if pos[y][x] != self.refpos[y][x]:
                    if self.refpos[y][x] != 0:
                        dpos[y][x] = 1
                    else:
                        dpos[y][x] = 2
        self.set_led(dpos)

    def set_led(self, pos):
        leds = [[0 for x in range(9)] for y in range(9)]
        cmd = "L20"
        for y in range(8):
            for x in range(8):
                if pos[y][x] != 0:
                    leds[7-x][y] = pos[y][x]
                    leds[7-x+1][y] = pos[y][x]
                    leds[7-x][y+1] = pos[y][x]
                    leds[7-x+1][y+1] = pos[y][x]
        for y in range(9):
            for x in range(9):
                if leds[y][x] == 0:
                    cmd = cmd + "00"
                elif leds[y][x] == 1:
                    cmd = cmd + "0F"
                else:
                    cmd = cmd + "F0"

        board.write(cmd)
        board.read(3)

    def set_led_off(self):
        cmd = "X"
        board.write(cmd)
        board.read(3)

    def position_to_fen(self, position):
        fen = ""
        blanks = 0
        for y in range(8):
            for x in range(8):
                f = position[7-y][x]
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        c = self.figrep['ascii'][i]
                        break
                if c == '?':
                    print(
                        "Internal FEN error, could not translation {} at {}{}".format(c, y, x))
                    return ""
                if c == '.':
                    blanks = blanks + 1
                else:
                    if blanks > 0:
                        fen += str(blanks)
                        blanks = 0
                    fen += c
            if blanks > 0:
                fen += str(blanks)
                blanks = 0
            if y < 7:
                fen += '/'
        fen += ' w KQkq - 0 1'
        return fen

    def fen_to_position(self, fen):
        position = [[0 for x in range(8)] for y in range(8)]
        fenp = fen[:fen.find(' ')]
        fi = 0
        for y in range(8):
            x = 0
            while x < 8:
                c = fenp[fi]
                fi += 1
                if c >= '1' and c <= '8':
                    x += int(c)
                    continue
                ci = -99
                for i in range(len(self.figrep['ascii'])):
                    if self.figrep['ascii'][i] == c:
                        ci = self.figrep['int'][i]
                        break
                if ci == -99:
                    print("Internal FEN2 error decoding {} at {}{}".format(c, y, x))
                    return []
                position[7-y][x] = ci
                x += 1
            if y < 7 and fenp[fi] != '/':
                print(
                    "Illegal fen: missing '/' {}{}: {}[{}]".format(y, x, fenp[fi], fi))
                return []
            fi += 1
        return position

    def print_position_ascii(self, position):
        print("  +------------------------+")
        for y in range(8):
            print("{} |".format(8-y), end="")
            for x in range(8):
                f = position[7-y][x]
                if (x+y) % 2 == 0:
                    f = f*-1
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        c = self.figrep['unic'][i]
                        break
                if (x+y) % 2 == 0:
                    print("\033[7m {} \033[m".format(c), end="")
                else:
                    print(" {} ".format(c), end='')
            print("|")
        print("  +------------------------+")
        print("    A  B  C  D  E  F  G  H")

    def event_worker_thread(self, callback):
        oldfen = ""
        while self.thread_active:
            for i in range(3):
                position = eboard.get_position()
                if position != None:
                    break
            fen = self.position_to_fen(position)
            if fen != oldfen:
                oldfen = fen
                callback(self, position, fen)
            time.sleep(0.2)

    def event_mon(self, callback):
        self.callback = callback
        if callback != None:
            self.thread_active = True
            self.event_thread = threading.Thread(
                target=self.event_worker_thread, args=(callback,))
            self.event_thread.setDaemon(True)
            self.event_thread.start()
        else:
            if self.event_thread != None:
                # self.event_thread.stop()
                self.thread_active = False
                self.event_thread = None

    def disconnect(self):
        if self.init:
            self.ser_port.close()
            self.init = False


def board_event(board, position, fen):
    eboard.print_position_ascii(position)
    print("FEN: {}".format(fen))
    if fen in valpos:
        engine.stop()
        engine.position(fen)
        engine.go(15)
    else:
        board.show_delta(position)


class SubHandler(chess.uci.InfoHandler):
    def post_info(self):
        # Called whenever a complete info line has been processed.
        # print(self.info)
        super().post_info()  # Release the lock

    def on_bestmove(self, bestmove, ponder):
        print("Best: {}".format(bestmove))
        super().on_bestmove(bestmove, ponder)

    def pv(self, move):
        print("PV: {}".format(move))
        super().pv(move)


class UciEngine:
    def __init__(self, engine_name):
        locations = ['/usr/bin', '/usr/local/bin', '/home/dsc/git/AI/LeelaChessZero/lc0/build/release',
                     '/Users/dsc/git/AI/LeelaChessZero/lc0/build/release']
        self.init = False
        for loc in locations:
            eng = os.path.join(loc, engine_name)
            if os.path.isfile(eng):
                self.engine = chess.uci.popen_engine(eng)
                self.engine.uci()
                self.info_handler = SubHandler()
                self.engine.info_handlers.append(self.info_handler)
                self.init = True
                return

    def go(self, time=0):
        if time == 0:
            ft = self.engine.go(infinite=True, async_callback=True)
        else:
            ft = self.engine.go(
                infinite=False, movetime=time*1000, async_callback=True)

    def stop(self):
        self.engine.stop()

    def position(self, fen):
        self.engine.position(chess.Board(fen))

    def name(self):
        return self.engine.name


if __name__ == '__main__':
    # engine = UciEngine('lc0')
    engine = UciEngine('stockfish')
    mboard = chess.Board()

    print(engine.name())

    eboard = MillenniumChess(verbose=True)
    if eboard.init:
        version = eboard.get_version()
        print("Millenium board version {} at {}".format(version, eboard.port))
        setup = False
        warn = False
        while not setup:
            pos = eboard.get_position()
            fen = eboard.position_to_fen(pos)
            if fen != "":
                mboard = chess.Board(fen)
                setup = True
            else:
                if warn is False:
                    warn = True
                    print("No position from board, waiting...")
                    time.sleep(1)

        eboard.set_reference()
        eboard.event_mon(board_event)
        time.sleep(10000)

        eboard.disconnect()
    else:
        print("No board.")
    print("closed.")
