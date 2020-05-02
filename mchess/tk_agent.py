import logging
import time
import threading
import copy
import os

import chess
import chess.pgn

from tkinter import *
from tkinter.ttk import *

import PIL
from PIL import ImageTk,Image,ImageOps

# By en:User:Cburnett - File:Chess klt45.svg, CC BY-SA 3.0, https://commons.wikimedia.org/w/index.php?curid=20363779
# https://commons.wikimedia.org/wiki/Template:SVG_chess_pieces
# convert -background none -density 128 -resize 128x Chess_bdt45.svg cbd.gif

class GameBoard(Frame):
    def __init__(self, parent,size=64, color1="white", color2="gray"):
        '''size is the size of a square, in pixels'''

        self.rows = 8
        self.columns = 8
        self.size = size
        self.color1 = color1
        self.color2 = color2
        self.height = None
        self.width = None
        self.pieces = {}
        self.figrep = {"png60": ["wp60.png", "wn60.png", "wb60.png", "wr60.png", "wq60.png", "wk60.png",
                                 "bp60.png", "bn60.png", "bb60.png", "br60.png", "bq60.png", "bk60.png"]}
        self.position = []

        for x in range(8):
            row=[]
            for y in range(9):
                row.append(-1)
            self.position.append(row)

        canvas_width = self.columns * size
        canvas_height = self.rows * size

        Frame.__init__(self, parent)
        self.canvas = Canvas(self, borderwidth=0, highlightthickness=0,
                                width=canvas_width, height=canvas_height, background="white")
        self.canvas.pack(fill="both", expand=True, padx=0, pady=0)
        self.load_figures(size)
        self.canvas.bind("<Configure>", self.refresh)

    def load_figures(self, size):
        self.png60s = []
        img_size = size-4
        for fn in self.figrep['png60']:
            fp = os.path.join('resources/pieces', fn)
            img = Image.open(fp).convert('RGBA').resize((img_size, img_size), Image.ANTIALIAS)
            self.png60s.append(ImageTk.PhotoImage(img))

    def refresh(self, event=None):
        redraw_fields=False
        if event is not None:
            if self.height != event.height or self.width != event.width:
                redraw_fields=True
                self.width=event.width
                self.height=event.height
                '''Redraw the board, possibly in response to window being resized'''
                xsize = int((self.width-1) / self.columns)
                ysize = int((self.height-1) / self.rows)
                self.size = min(xsize, ysize)
                self.load_figures(self.size)

        if redraw_fields is True:
            self.canvas.delete("square")
        self.canvas.delete("piece")
        color = self.color2
        for row in range(self.rows):
            color = self.color1 if color == self.color2 else self.color2
            for col in range(self.columns):
                x1 = (col * self.size)
                y1 = (row * self.size)
                x2 = x1 + self.size
                y2 = y1 + self.size
                if redraw_fields is True:
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=color, tags="square")
                color = self.color1 if color == self.color2 else self.color2
                img_ind = self.position[row][col]
                if img_ind != -1:
                    self.canvas.create_image(x1, y1, image=self.png60s[img_ind], tags=("piece"), anchor="nw")
        self.canvas.tag_raise("piece")
        self.canvas.tag_lower("square")


class TkAgent:
    def __init__(self, appque, prefs):
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "png60": ["wp60.png", "wn60.png", "wb60.png", "wr60.png", "wq60.png", "wk60.png",
                                 "bp60.png", "bn60.png", "bb60.png", "br60.png", "bq60.png", "bk60.png"],
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        self.name = 'TkAgent'
        self.prefs = prefs
        self.log = logging.getLogger("TkAgent")
        self.appque = appque
        self.orientation = True
        self.active = False
        self.agent_state_cache = {}
        self.tk_moves = []
        self.png60s = None
        self.title_text = None

        self.tk_board = None
        self.tk_board2 = None
        self.title = None
        self.gui_init = False

        self.tkapp_thread_active = True

        self.tkapp_thread = threading.Thread(
            target=self.tkapp_worker_thread, args=(self.appque, self.log))
        self.tkapp_thread.setDaemon(True)
        self.tkapp_thread.start()

        t0 = time.time()
        warned = False
        while self.gui_init is False:
            time.sleep(0.1)
            if time.time()-t0 > 2 and warned is False:
                warned = True
                self.log.error("Tk GUI is not responding in time!")
            if time.time()-t0 > 5:
                return
        self.log.info("GUI online.")
        self.active = True


    def agent_ready(self):
        return self.active

    def quit(self):
        self.tkapp_thread_active = False

    def board2pos(self, board):
        pos=[]
        for y in reversed(range(8)):
            ti = "{} |".format(y+1)
            row=[]
            for x in range(8):
                fig = board.piece_at(chess.square(x, y))
                if fig is not None:
                    ind=0
                    for f0 in self.figrep['pythc']:
                        if fig.piece_type == f0[0] and fig.color == f0[1]:
                            break
                        ind += 1
                    if ind < len(self.figrep['pythc']):
                        row.append(ind)
                    else:
                        row.append(-1)
                        self.log.error(f'Figure conversion error at {x}{y}')
                else:
                    row.append(-1)
            pos.append(row)
        return pos

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        self.log.info("display_board")
        if self.gui_init is False:
            return
        self.title_text.set(attribs["white_name"] + " - " + attribs["black_name"])
        self.tk_board.position = self.board2pos(board)
        self.tk_board.refresh()

    def display_move(self, move_msg):
        pass

    def display_info(self, board, info, max_board_preview_hmoves=6):
        ninfo = copy.deepcopy(info)
        nboard = copy.deepcopy(board)
        nboard_cut = copy.deepcopy(nboard)
        max_cut=max_board_preview_hmoves
        if 'variant' in ninfo:
            ml = []
            mv = ''
            if nboard.turn is False:
                mv = (nboard.fullmove_number,)
                mv += ("..",)
            rel_mv=0
            for move in ninfo['variant']:
                if move is None:
                    self.log.error("None-move in variant: {}".format(ninfo))
                if nboard.turn is True:
                    mv = (nboard.fullmove_number,)
                try:
                    san = nboard.san(move)
                except Exception as e:
                    self.log.warning(
                        "Internal error '{}' at san conversion.".format(e))
                    san = None
                if san is not None:
                    mv += (san,)
                else:
                    self.log.info(
                        "Variant cut off due to san-conversion-error: '{}'".format(mv))
                    break
                if nboard.turn is False:
                    ml.append(mv)
                    mv = ""
                nboard.push(move)
                if rel_mv < max_cut:
                    nboard_cut.push(move)
                    rel_mv += 1
            if mv != "":
                ml.append(mv)
                mv = ""
            ninfo['variant'] = ml
        self.tk_board2.position = self.board2pos(nboard_cut)
        self.tk_board2.refresh()
        # msg = {'fenref': nboard_cut.fen(), 'info': ninfo}

    def agent_states(self, msg):
        self.agent_state_cache[msg['actor']] = msg

    def set_valid_moves(self, board, vals):
        self.tk_moves = []
        if vals != None:
            for v in vals:
                self.tk_moves.append(vals[v])

    def tkapp_worker_thread(self, appque, log):
        root = Tk()
        self.tk_board = GameBoard(root)
        self.tk_board2 = GameBoard(root)
        self.title_text = StringVar()
        self.title = Label(textvariable=self.title_text)
        self.title.pack()
        self.tk_board.pack(side="left", fill="both", expand="false", padx=2, pady=2)
        self.tk_board2.pack(side="right", fill="both", expand="false", padx=2, pady=2)
    
        menubar = Menu(self.tk_board.master)
        self.tk_board.master.config(menu=menubar)

        fileMenu = Menu(menubar)
        fileMenu.add_command(label="New Game", command=self.onNew)
        fileMenu.add_command(label="Go", command=self.onGo)
        fileMenu.add_command(label="Back", command=self.onBack)
        fileMenu.add_command(label="Stop", command=self.onStop)
        fileMenu.add_command(label="Analyse", command=self.onAnalyse)
        fileMenu.add_command(label="Exit", command=self.onExit)

        menubar.add_cascade(label="File", menu=fileMenu)

        self.gui_init = True
        root.mainloop()

    def onNew(self):
        self.appque.put({'new game': '', 'actor': self.name})

    def onGo(self):
        self.appque.put({'go': 'current', 'actor': self.name})

    def onBack(self):
        self.appque.put({'back': '', 'actor': self.name})

    def onStop(self):
        self.appque.put({'stop': '', 'actor': self.name})

    def onAnalyse(self):
        self.appque.put({'analysis': '', 'actor': self.name})

    def onExit(self):
        self.appque.put({'quit': '', 'actor': self.name})

