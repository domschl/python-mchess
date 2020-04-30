import logging
import time
import threading
import queue
import json
import copy

import chess
import chess.pgn

from tkinter import *
# from tkinter.ttk import *

import PIL
from PIL import ImageTk,Image,ImageOps
# By en:User:Cburnett - File:Chess klt45.svg, CC BY-SA 3.0, https://commons.wikimedia.org/w/index.php?curid=20363779
# https://stackoverflow.com/questions/4954395/create-board-game-like-grid-in-python
# https://commons.wikimedia.org/wiki/File:Chess_bdt45.svg
# https://commons.wikimedia.org/wiki/Template:SVG_chess_pieces
# convert -background none -density 128 -resize 128x Chess_bdt45.svg cbd.gif

class GameBoard(Frame):
    def __init__(self, parent,size=64, color1="white", color2="gray"):
        '''size is the size of a square, in pixels'''

        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE), (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE), (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK), (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK), (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.chesssym = {"unic": ["-", "×", "†", "‡", "½"],
                         "ascii": ["-", "x", "+", "#", "1/2"]}

        self.rows = 8
        self.columns = 8
        self.size = size
        self.color1 = color1
        self.color2 = color2
        self.pieces = {}

        canvas_width = self.columns * size
        canvas_height = self.rows * size

        Frame.__init__(self, parent)
        self.canvas = Canvas(self, borderwidth=0, highlightthickness=0,
                                width=canvas_width, height=canvas_height, background="white")
        self.canvas.pack(fill="both", expand=False, padx=0, pady=0)

        # this binding will cause a refresh if the user interactively
        # changes the window size
        self.canvas.bind("<Configure>", self.refresh)

    def addpiece(self, name, image, row=0, column=0):
        '''Add a piece to the playing board'''
        self.canvas.create_image(0, 0, image=image, tags=(name, "piece"), anchor="c")
        self.placepiece(name, row, column)

    def placepiece(self, name, row, column):
        '''Place a piece at the given row/column'''
        self.pieces[name] = (row, column)
        x0 = (column * self.size) + int(self.size/2)
        y0 = (row * self.size) + int(self.size/2)
        self.canvas.coords(name, x0, y0)

    def refresh(self, event):
        '''Redraw the board, possibly in response to window being resized'''
        xsize = int((event.width-1) / self.columns)
        ysize = int((event.height-1) / self.rows)
        self.size = min(xsize, ysize)
        self.canvas.delete("square")
        color = self.color2
        for row in range(self.rows):
            color = self.color1 if color == self.color2 else self.color2
            for col in range(self.columns):
                x1 = (col * self.size)
                y1 = (row * self.size)
                x2 = x1 + self.size
                y2 = y1 + self.size
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=color, tags="square")
                color = self.color1 if color == self.color2 else self.color2
        for name in self.pieces:
            self.placepiece(name, self.pieces[name][0], self.pieces[name][1])
        self.canvas.tag_raise("piece")
        self.canvas.tag_lower("square")


class TkAgent:
    def __init__(self, appque, prefs):
        self.name = 'TkAgent'
        self.prefs = prefs
        self.log = logging.getLogger("TkAgent")
        self.appque = appque
        self.orientation = True
        self.active = False
        self.agent_state_cache={}


        self.tkapp_thread_active = True

        self.tkapp_thread = threading.Thread(
            target=self.tkapp_worker_thread, args=(self.appque, self.log))
        self.tkapp_thread.setDaemon(True)
        self.tkapp_thread.start()

        self.active = True


    def agent_ready(self):
        return self.active

    def quit(self):
        self.tkapp_thread_active = False

    def display_board(self, board, attribs={'unicode': True, 'invert': False, 'white_name': 'white', 'black_name': 'black'}):
        self.last_board = board
        self.last_attribs = attribs
        try:
            game = chess.pgn.Game().from_board(board)
            game.headers["White"] = attribs["white_name"]
            game.headers["Black"] = attribs["black_name"]
            pgntxt = str(game)
        except Exception as e:
            self.log.error("Invalid PGN position, {}".format(e))
            return
        self.last_pgn = pgntxt
        # print("pgn: {}".format(pgntxt))
        msg = {'fen': board.fen(), 'pgn': pgntxt, 'attribs': attribs}
        self.log.debug(msg)

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

        msg = {'fenref': nboard_cut.fen(), 'info': ninfo}

    def agent_states(self, msg):
        self.agent_state_cache[msg['actor']] = msg

    def set_valid_moves(self, board, vals):
        self.socket_moves = []
        if vals != None:
            for v in vals:
                self.socket_moves.append(vals[v])

    def tkapp_worker_thread(self, appque, log):
        root = Tk()
        board = GameBoard(root)
        board2 = GameBoard(root)
        title=Label(text="mChess tk/inter")
        title.pack()
        board.pack(side="left", fill="both", expand="false", padx=2, pady=2)
        board2.pack(side="right", fill="both", expand="false", padx=2, pady=2)
        img=Image.open("resources/pieces/wk60.png").convert('RGBA') # /home/dsc/git/PScratch/chesstests/Chess_klt60.png")
        player1 = ImageTk.PhotoImage(img)
        img=Image.open("resources/pieces/bb60.png").convert('RGBA')
        player2 = ImageTk.PhotoImage(img)
        board.addpiece("player1", player1, 7, 4)
        # board.addpiece("player1", player1, 0, 4)
        board.addpiece("player2", player2, 0, 3)
        board2.addpiece("player3", player2, 0, 2)

        menubar = Menu(board.master)
        board.master.config(menu=menubar)

        fileMenu = Menu(menubar)
        fileMenu.add_command(label="Exit", command=self.onExit)
        menubar.add_cascade(label="File", menu=fileMenu)

        root.mainloop()

    def onExit(self):
        pass
