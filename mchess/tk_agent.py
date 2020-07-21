import logging
import time
import threading
import copy
import os

import chess
import chess.pgn

# from tkinter import *
# from tkinter.ttk import *
# from tkinter import filedialog, font

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import font, filedialog

import PIL
from PIL import ImageTk, Image, ImageOps

# By en:User:Cburnett - File:Chess klt45.svg, CC BY-SA 3.0,
# https://commons.wikimedia.org/w/index.php?curid=20363779
# https://commons.wikimedia.org/wiki/Template:SVG_chess_pieces
# convert -background none -density 128 -resize 128x Chess_bdt45.svg cbd.gif


class GameBoard(ttk.Frame):
    def __init__(self, parent, size=64, r=0, c=0, color1="white", color2="gray",
                 bg_color="black", ol_color="black", log=None):
        '''size is the size of a square, in pixels'''

        self.rows = 8
        self.log = log
        self.columns = 8
        self.size = size
        self.color1 = color1
        self.color2 = color2
        self.bg_color = bg_color
        self.ol_color = ol_color
        self.height = None
        self.width = None
        self.pieces = {}
        self.figrep = {"png60": ["wp60.png", "wn60.png", "wb60.png", "wr60.png", "wq60.png",
                                 "wk60.png", "bp60.png", "bn60.png", "bb60.png", "br60.png",
                                 "bq60.png", "bk60.png"]}
        self.position = []
        self.valid_move_list = []
        self.move_part = 0
        self.move_actor = None
        self.cur_move = ""

        for _ in range(8):
            row = []
            for _ in range(8):
                row.append(-1)
            self.position.append(row)

        canvas_width = self.columns * size
        canvas_height = self.rows * size

        ttk.Frame.__init__(self, parent)
        self.canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0,
                                width=canvas_width, height=canvas_height, background=bg_color)
        self.canvas.grid(row=r, column=c, sticky="news")
        # self.canvas.grid_columnconfigure(0, weight=1)
        # self.canvas.grid_rowconfigure(0, weight=1)
        self.load_figures(size)
        self.canvas.bind("<Configure>", self.refresh)
        self.canvas.bind("<Button-1>", self.mouse_click)

    def load_figures(self, size):
        self.png60s = []
        img_size = size-4
        for fn in self.figrep['png60']:
            fp = os.path.join('resources/pieces', fn)
            img = Image.open(fp).convert('RGBA').resize(
                (img_size, img_size), Image.ANTIALIAS)
            self.png60s.append(ImageTk.PhotoImage(img))

    def mouse_click(self, event):
        x = chr(event.x//self.size+ord('a'))
        y = chr(7-(event.y//self.size)+ord('1'))
        if self.move_part == 0:
            cc = f"{x}{y}"
            self.cur_move = ""
        else:
            cc = f"{self.cur_move}{x}{y}"
        if len(self.valid_move_list) > 0:
            f = []
            for mv in self.valid_move_list:
                if mv[0:self.move_part*2+2] == cc:
                    f.append(mv)
            if len(f) > 0:
                if self.move_part == 0:
                    self.cur_move = cc
                    self.move_part += 1
                    return
                else:
                    if len(f) > 1 and self.log is not None:
                        self.log.error("This is non-implemented situation")
                        # XXX: select pawn upgrade GUI
                    self.move_actor(f[0])
            else:
                if self.log is not None:
                    self.log.warning("Invalid entry!")
                self.move_part = 0
                self.cur_move = ""
        else:
            if self.log is not None:
                self.log.warning(
                    "You are not allowed to click on the board at this time!")
            self.move_part = 0
            self.cur_move = 0

        print(f"Click at {cc}")

    def register_moves(self, move_list, move_actor=None):
        print(move_list)
        self.move_actor = move_actor
        self.move_part = 0
        self.valid_move_list = move_list

    def refresh(self, event=None):
        redraw_fields = False
        if event is not None:
            if self.height != event.height or self.width != event.width:
                redraw_fields = True
                self.width = event.width
                self.height = event.height
                # Redraw the board, possibly in response to window being resized
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
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.ol_color,
                                                 fill=color, tags="square")
                color = self.color1 if color == self.color2 else self.color2
                img_ind = self.position[row][col]
                if img_ind != -1:
                    self.canvas.create_image(x1, y1, image=self.png60s[img_ind],
                                             tags=("piece"), anchor="nw")
        self.canvas.tag_raise("piece")
        self.canvas.tag_lower("square")


class TkAgent:
    def __init__(self, appque, prefs):
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "pythc": [(chess.PAWN, chess.WHITE), (chess.KNIGHT, chess.WHITE),
                                 (chess.BISHOP, chess.WHITE), (chess.ROOK, chess.WHITE),
                                 (chess.QUEEN, chess.WHITE), (chess.KING, chess.WHITE),
                                 (chess.PAWN, chess.BLACK), (chess.KNIGHT, chess.BLACK),
                                 (chess.BISHOP, chess.BLACK), (chess.ROOK, chess.BLACK),
                                 (chess.QUEEN, chess.BLACK), (chess.KING, chess.BLACK)],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "png60": ["wp60.png", "wn60.png", "wb60.png", "wr60.png", "wq60.png",
                                 "wk60.png", "bp60.png", "bn60.png", "bb60.png", "br60.png",
                                 "bq60.png", "bk60.png"],
                       "ascii": "PNBRQK.pnbrqk"}
        self.turquoise = {
            "light": "#D8DBE2",  # Gainsboro
            "dlight": "#A9BCC0",  # Pastel Blue
            "turquoise": "#58A4B0",  # Cadet Blue
            "silver": "#C0C0C0",  # Silver
            "darkgray": "#A9A9A9",  # Darkgray
            "ldark": "#373F41",  # Charcoil
            "dark": "#2E3532",  # Jet
            "ddark": "#282A32",  # Charleston Green
            "dddark": "#1B1B1E",  # Eerie Black
            "xdddark": "#202022",  # X Black
        }
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

        self.board = None
        self.tk_board = None
        self.tk_board2 = None
        self.title = None
        self.movelist = None
        self.analist = None
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
        pos = []
        for y in reversed(range(8)):
            row = []
            for x in range(8):
                fig = board.piece_at(chess.square(x, y))
                if fig is not None:
                    ind = 0
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

    def display_board(self, board, attribs={'unicode': True, 'invert': False,
                                            'white_name': 'white', 'black_name': 'black'}):
        self.log.info("display_board")
        if self.gui_init is False:
            return
        self.title_text.set(attribs["white_name"] +
                            " - " + attribs["black_name"])
        self.tk_board.position = self.board2pos(board)
        self.tk_board.refresh()

        try:
            game = chess.pgn.Game().from_board(board)
            game.headers["White"] = attribs["white_name"]
            game.headers["Black"] = attribs["black_name"]
            pgntxt = str(game)
            pgntxt = ''.join(pgntxt.splitlines()[8:])
        except Exception as e:
            self.log.error(f"Invalid PGN position, {e}")
            return
        self.movelist.delete("1.0", tk.END)
        self.movelist.insert("1.0", pgntxt)

    def display_move(self, move_msg):
        pass

    def display_info(self, board, info, max_board_preview_hmoves=6):
        # if info['multipv_ind'] != 1:
        #     return
        mpv_ind = info['multipv_ind']
        ninfo = copy.deepcopy(info)
        nboard = copy.deepcopy(board)
        nboard_cut = copy.deepcopy(nboard)
        max_cut = max_board_preview_hmoves
        if 'variant' in ninfo:
            ml = []
            mv = ''
            if nboard.turn is False:
                mv = (nboard.fullmove_number,)
                mv += ("..",)
            rel_mv = 0
            for move in ninfo['variant']:
                if move is None:
                    self.log.error(f"None-move in variant: {ninfo}")
                if nboard.turn is True:
                    mv = (nboard.fullmove_number,)
                try:
                    san = nboard.san(move)
                except Exception as e:
                    self.log.warning(
                        f"Internal error '{e}' at san conversion.")
                    san = None
                if san is not None:
                    mv += (san,)
                else:
                    self.log.info(
                        f"Variant cut off due to san-conversion-error: '{mv}'")
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
        self.analist.delete(f"{mpv_ind}.0", f"{mpv_ind+1}.0")
        self.analist.insert(f"{mpv_ind}.0", f"[{mpv_ind}]: " + str(ml) + "\n")
        if mpv_ind == 1:
            self.tk_board2.position = self.board2pos(nboard_cut)
            self.tk_board2.refresh()

    def agent_states(self, msg):
        self.agent_state_cache[msg['actor']] = msg

    def do_move(self, move):
        self.appque.put({'move': {'uci': move, 'actor': self.name}})

    def set_valid_moves(self, board, vals):
        tk_moves = []
        self.board = board
        if vals is not None:
            for v in vals:
                tk_moves.append(vals[v])
        self.tk_board.register_moves(tk_moves, self.do_move)

    def tkapp_worker_thread(self, appque, log):
        root = tk.Tk()
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(size=10)
        fixed_font = font.nametofont("TkFixedFont")
        fixed_font.configure(size=10)
        # self.frame = Frame(root)
        for i in range(3):
            tk.Grid.columnconfigure(root, i, weight=1)
 #           if i>0:
            tk.Grid.rowconfigure(root, i, weight=1)
        # for i in range(3):
        #     Grid.columnconfigure(self.frame, i, weight=1)
        #     Grid.rowconfigure(self.frame, i, weight=1)
        # self.frame.grid(sticky=N+S+W+E)

        self.bof = ttk.Frame(root)
        for i in range(3):
            tk.Grid.columnconfigure(self.bof, i, weight=1)
 #           if i>0:
            tk.Grid.rowconfigure(self.bof, i, weight=1)

        self.bof.grid(row=1, column=0, sticky="news")
        self.tk_board = GameBoard(self.bof, log=self.log, r=1, c=0,
                                  color1=self.turquoise['dlight'],
                                  color2=self.turquoise['turquoise'],
                                  bg_color=self.turquoise['ldark'],
                                  ol_color=self.turquoise['darkgray'])
        self.tk_board.grid(row=1, column=0, sticky="news")

        s = 20
        self.bfr = ttk.Frame(self.bof)
        self.bfr.grid(row=2, column=0, sticky="news")
        img = Image.open(
            'web/images/bb.png').convert('RGBA').resize((s, s), Image.ANTIALIAS)
        bbackimg = ImageTk.PhotoImage(img)
        self.button_bback = ttk.Button(
            self.bfr, image=bbackimg, command=self.on_fast_back)
        # background=self.turquoise['dlight'], , relief=FLAT)
        # self.button_bback.configure(padx=15, pady=15)
        self.button_bback.grid(
            row=0, column=0, sticky="ew", padx=(5, 5), pady=(7, 7))
        img = Image.open(
            'web/images/b.png').convert('RGBA').resize((s, s), Image.ANTIALIAS)
        backimg = ImageTk.PhotoImage(img)
        self.button_back = ttk.Button(
            self.bfr, image=backimg, command=self.on_back)
        # , relief=FLAT)
        self.button_back.grid(row=0, column=1, sticky="ew",
                              padx=(5, 5), pady=(7, 7))
        img = Image.open(
            'web/images/stop.png').convert('RGBA').resize((s, s), Image.ANTIALIAS)
        stopimg = ImageTk.PhotoImage(img)
        self.button_stop = ttk.Button(
            self.bfr, image=stopimg, command=self.on_stop)
        # , relief=FLAT)
        self.button_stop.grid(row=0, column=2, sticky="ew",
                              padx=(8, 8), pady=(7, 7))
        img = Image.open(
            'web/images/f.png').convert('RGBA').resize((s, s), Image.ANTIALIAS)
        forimg = ImageTk.PhotoImage(img)
        self.button_forward = ttk.Button(
            self.bfr, image=forimg, command=self.on_forward)
        # , relief=FLAT)
        self.button_forward.grid(
            row=0, column=3, sticky="ew", padx=(5, 5), pady=(7, 7))
        img = Image.open(
            'web/images/ff.png').convert('RGBA').resize((s, s), Image.ANTIALIAS)
        fforimg = ImageTk.PhotoImage(img)
        self.button_fforward = ttk.Button(
            self.bfr, image=fforimg, command=self.on_fast_forward)
        # , relief=FLAT)
        self.button_fforward.grid(
            row=0, column=4, sticky="ew", padx=(5, 5), pady=(7, 7))

        self.tk_board2 = GameBoard(root, log=self.log, r=1, c=2, color1=self.turquoise['dlight'],
                                   color2=self.turquoise['turquoise'],
                                   bg_color=self.turquoise['ldark'],
                                   ol_color=self.turquoise['darkgray'])
        self.movelist = tk.Text(root)
        self.analist = tk.Text(root, height=10)
        self.title_text = tk.StringVar()
        self.title = ttk.Label(root, textvariable=self.title_text)

        self.title.grid(row=0, column=0, sticky="ew")
        self.movelist.grid(row=1, column=1, sticky="news")
        self.tk_board2.grid(row=1, column=2, sticky="news")
        self.analist.grid(row=2, column=2, sticky="ew")

        menubar = tk.Menu(root)
        root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Game", command=self.on_new, underline=0,
                              accelerator="Ctrl+n")
        root.bind_all("<Control-n>", self.on_new)
        file_menu.add_separator()
        file_menu.add_command(label="Open PGN file...", command=self.on_pgn_open, underline=0,
                              accelerator="Ctrl+o")
        root.bind_all("<Control-o>", self.on_pgn_open)
        file_menu.add_command(label="Save PGN file...", command=self.on_pgn_save, underline=0,
                              accelerator="Ctrl+s")
        root.bind_all("<Control-s>", self.on_pgn_save)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit, underline=1,
                              accelerator="Ctrl+x")
        root.bind_all("<Control-x>", self.on_exit)

        game_menu = tk.Menu(menubar, tearoff=0)

        submenu = tk.Menu(game_menu)
        submenu.add_command(label="Player - Player", command=self.on_mode_pp)
        submenu.add_command(label="Player - Engine", command=self.on_mode_pe)
        submenu.add_command(label="Engine - Player", command=self.on_mode_ep)
        submenu.add_command(label="Engline - Engine", command=self.on_mode_ee)
        game_menu.add_cascade(label="Game mode", menu=submenu, underline=6)

        game_menu.add_separator()
        game_menu.add_command(label="Go", command=self.on_go,
                              underline=0, accelerator="Ctrl+g")
        root.bind_all("<Control-g>", self.on_go)
        game_menu.add_command(
            label="Beginning", command=self.on_fast_back, underline=0)
        game_menu.add_command(label="Back", command=self.on_back, underline=0,
                              accelerator="Ctrl+b")
        root.bind_all("<Control-b>", self.on_back)
        game_menu.add_command(label="Forward", command=self.on_forward, underline=0,
                              accelerator="Ctrl+f")
        root.bind_all("<Control-f>", self.on_forward)
        game_menu.add_command(
            label="End", command=self.on_fast_forward, underline=0)
        game_menu.add_separator()
        game_menu.add_command(label="Stop", command=self.on_stop, underline=1,
                              accelerator="Ctrl+t")
        root.bind_all("<Control-t>", self.on_stop)
        game_menu.add_separator()
        game_menu.add_command(label="Analyse", command=self.on_analyse, underline=0,
                              accelerator="Ctrl+a")
        root.bind_all("<Control-a>", self.on_analyse)

        menubar.add_cascade(label="File", menu=file_menu, underline=0)
        menubar.add_cascade(label="Game", menu=game_menu, underline=0)

        self.gui_init = True
        root.mainloop()

    def on_new(self, event=None):
        self.appque.put({'new game': '', 'actor': self.name})

    def on_go(self, event=None):
        self.appque.put({'go': 'current', 'actor': self.name})

    def on_back(self, event=None):
        self.appque.put({'back': '', 'actor': self.name})

    def on_fast_back(self, event=None):
        self.appque.put({'fast-back': '', 'actor': self.name})

    def on_forward(self, event=None):
        self.appque.put({'forward': '', 'actor': self.name})

    def on_fast_forward(self, event=None):
        self.appque.put({'fast-forward': '', 'actor': self.name})

    def on_stop(self, event=None):
        self.appque.put({'stop': '', 'actor': self.name})

    def on_analyse(self, event=None):
        self.appque.put({'analysis': '', 'actor': self.name})

    def on_exit(self, event=None):
        self.appque.put({'quit': '', 'actor': self.name})

    def on_mode_pp(self, event=None):
        self.appque.put({'game_mode': 'PLAYER_PLAYER'})

    def on_mode_pe(self, event=None):
        self.appque.put({'game_mode': 'PLAYER_ENGINE'})

    def on_mode_ep(self, event=None):
        self.appque.put({'game_mode': 'ENGINE_PLAYER'})

    def on_mode_ee(self, event=None):
        self.appque.put({'game_mode': 'ENGINE_ENGINE'})

    def load_pgns(self, fn):
        try:
            with open(fn, 'r') as f:
                d = f.read()
        except Exception as e:
            print(f"Failed to read {fn}: {e}")
            return None
        pt = d.split('\n\n')
        if len(pt) % 2 != 0:
            print("Bad structure or incomplete!")
            return None
        if len(pt) == 0:
            print("Empty")
            return None
        games = []
        for i in range(0, len(pt), 2):
            gi = pt[i]+"\n\n"+pt[i+1]
            games.append(gi)
        return games

    def on_pgn_open(self, event=None):
        filename = filedialog.askopenfilename(initialdir=".", title="Select PGN file",
                                              filetypes=(("pgn files", "*.pgn"),
                                                         ("all files", "*.*")))
        games = self.load_pgns(filename)
        if len(games) > 1:
            self.log.warning(
                f'File contained {len(games)}, only first game read.')
        if games is not None:
            self.appque.put({'pgn_game': {'pgn_data': games[0]}})

    def on_pgn_save(self, event=None):
        filename = filedialog.asksaveasfilename(initialdir=".",
                                                title="Select PGN file",
                                                filetypes=(("pgn files", "*.pgn"),
                                                           ("all files", "*.*")))
        print(filename)
