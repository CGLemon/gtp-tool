import sys
import argparse
import core.game as game
import core.render_helper as render
import tkinter as tk
import tkinter.font as font
from functools import partial
from core.gtp import GtpVertex, GtpColor, GtpEngine
from core.game import Stone

class GuiGtpEngine(GtpEngine):
    def __init__(self, command):
        super().__init__(command)
        self.raise_err = True

    def gui_color_to_gtp_color(self, val):
        if val == Stone.BLACK:
            return GtpColor(GtpColor.BLACK)
        if val == Stone.WHITE:
            return GtpColor(GtpColor.WHITE)
        return GtpColor(GtpColor.INVLD)

    def play_pass(self, gui_color):
        color = self.gui_color_to_gtp_color(gui_color)
        self.play(str(color), str(GtpVertex(GtpVertex.PASS_VERTEX)))

    def play_move(self, gui_color, x, y):
        color = self.gui_color_to_gtp_color(gui_color)
        self.play(str(color), str(GtpVertex((x, y))))

    def genmove_and_return(self, gui_color):
        color = self.gui_color_to_gtp_color(gui_color)
        return GtpVertex(self.genmove(str(color)))

    def quit_and_shutdown(self):
        self.quit()
        self.shutdown()

class Gui():
    def __init__(self, args):
        self.game_type = args.game.lower()
        self.board_size = args.boardsize

        self.width = 1200
        self.height = 900

        self._root = tk.Tk()
        self._root.resizable(True, True)
        self._root.title("GUI")
        self._root.geometry("{w}x{h}".format(w=self.width, h=self.height))

        self._frames = list()
        self._init_layout()
        self._lock = False
        self._engine = None
        self._engine_color = None
        if not args.engine_color.lower() in ["black", "white"]:
            raise Exception("Invalid engine color.")
        else:
            if args.engine_color.lower() == "black":
                self._engine_color = Stone.BLACK
            elif args.engine_color.lower() == "white":
                self._engine_color = Stone.WHITE
        if not args.command is None:
            sys.stderr.write("Engine is {}.\n".format(self._engine_color))
            self._engine = GuiGtpEngine(args.command)
            self._init_engine()
        self._render()
        self._root.mainloop()

    def _setup_game(self, frame, size):
        self._game = None
        self.board_canvas = None

        if self.game_type == "go":
            self.board_size = 19 if self.board_size <= 0 else self.board_size
            self._game = game.GoGame(self.board_size)
            self.board_canvas = render.GoLikeBoard(frame, self.board_size, size)
            self._root.title("Go")
        elif self.game_type == "gomoku":
            self.board_size = 15 if self.board_size <= 0 else self.board_size
            self._game = game.GomokuGame(self.board_size)
            self.board_canvas = render.GoLikeBoard(frame, self.board_size, size)
            self._root.title("Gomoku")
        elif self.game_type == "nogo":
            self.board_size = 9 if self.board_size <= 0 else self.board_size
            self._game = game.NoGoGame(self.board_size)
            self.board_canvas = render.GoLikeBoard(frame, self.board_size, size)
            self._root.title("NoGo")
        elif self.game_type == "othello":
            self.board_size = 8 if self.board_size <= 0 else self.board_size
            self._game = game.OthelloGame(self.board_size)
            self.board_canvas = render.OthelloLikeBoard(frame, self.board_size, size)
            self._root.title("Othello")
        else:
            raise Exception("Unsupported game.")

    def _init_layout(self):
        ratio = [0.9, 0.1]
        sizebase = self.height

        # board part
        board_frame_size = ratio[0] * sizebase
        self._board_frame = tk.Frame(
            self._root,
            width=self.width,
            height=round(board_frame_size))
        self._board_frame.grid(column=0, row=0)
        self._frames.append(self._board_frame)

        canvas_size = round(ratio[0] * sizebase * 0.95)
        xstart = (self.width - canvas_size) // 2
        ystart = (board_frame_size - canvas_size) // 2

        canvas_frame = tk.Frame(
            self._root,
            width=canvas_size,
            height=self.height)
        canvas_frame.place(x=xstart, y=ystart)

        self._setup_game(canvas_frame, canvas_size)
        self.board_canvas.bind_wrapper(self._play_at)
        self.board_canvas.sync(self._game)
        self.board_canvas.render()

        # menu part
        self._menu_frame = tk.Frame(
            self._root,
            width=self.width,
            height=round(ratio[1] * sizebase))
        self._menu_frame.grid(column=0, row=1)
        self._frames.append(self._menu_frame)

        restart_btn = tk.Button(
            self._menu_frame, text="restart",
            width=10, height=1,
            font=font.Font(size=15), command=self._restart)
        restart_btn.pack(side=tk.LEFT, padx=10)

        try:
            self._game.pass_legal()
            pass_btn = tk.Button(
                self._menu_frame, text="pass",
                width=10, height=1,
                font=font.Font(size=15), command=self._play_pass)
            pass_btn.pack(side=tk.LEFT, padx=10)
        except:
            pass

    def _destroy(self):
        for f in self._frames:
            f.destroy()
        self._frames.clear()

    def _restart(self):
        if self._lock:
            sys.stderr.write("The board is locked.\n")
            return
        self._destroy()
        self._init_layout()
        sys.stderr.write("Restart the game.\n")
        if self.is_engine_valid():
            self._init_engine()

    def _play_pass(self):
        if self._lock:
            sys.stderr.write("The board is locked.\n")
            return
        self._lock = True
        query = dict()
        if self._game.pass_legal():
            query["pass"] = True
        else:
            sys.stderr.write("Pass is not legal move.\n")
        self._play_move_query(query)

    def _play_at(self, x, y):
        if self._lock:
            sys.stderr.write("The board is locked.\n")
            return
        self._lock = True
        query = dict()
        self.board_canvas.sync(self._game)
        if self._game.legal(x, y, self._game.tomove):
            query["move"] = True
            query["coordinate"] = (x, y)
        else:
            query["illegal"] = True
            query["coordinate"] = (x, y)
        self._play_move_query(query)

    def _play_move_query(self, query):
        engine_play = False
        try:
            tomove = self._game.tomove
            if query.get("pass", False):
                self._game.play_pass()
                sys.stderr.write("Play the pass move.\n")
                if self.is_engine_valid():
                    self._engine.play_pass(tomove)
                    engine_play = True
            elif query.get("move", False):
                x, y = query["coordinate"]
                self._game.play(x, y, self._game.tomove)
                self.board_canvas.sync(self._game)
                self.board_canvas.render()
                sys.stderr.write("Play the move at {}-{}.\n".format(x, y))
                if self.is_engine_valid():
                    self._engine.play_move(tomove, x, y)
                    engine_play = True
            elif query.get("illegal", False):
                x, y = query["coordinate"]
                self.board_canvas.sethint(x, y, render.BoardCanvas.ILLEGAL)
                self.board_canvas.render()
                sys.stderr.write("The {}-{} is not legal move.\n".format(x, y))
        except Exception as err:
            sys.stderr.write("Engine thinks you play a illegal move.\n")

        if engine_play:
            self._root.after(10, self._engine_play_and_unlock)
        else:
            self._lock = False

    def _engine_play_and_unlock(self):
        if self._engine_color != self._game.tomove:
            self._lock = False
            return
        try:
            # TODO: check the vertex is legal or not
            vtx = self._engine.genmove_and_return(self._game.tomove)
            if vtx.is_pass():
                self._game.play_pass()
                sys.stderr.write("Engine playes pass move.\n")
            elif vtx.is_move():
                x, y = vtx.get()
                self._game.play(x, y, self._game.tomove)
                self.board_canvas.sync(self._game)
                self.board_canvas.render()
                sys.stderr.write("Engine the move at {}-{}.\n".format(x, y))
            else:
                raise Exception("Game is over!")
        except Exception as err:
            sys.stderr.write("{}\n".format(err))           
        self._lock = False

    def _render(self):
        self.board_canvas.sync(self._game)
        self.board_canvas.render()

    def is_engine_valid(self):
        return not self._engine is None

    def _init_engine(self):
       self._engine.clear_board()
       self._engine.boardsize(self.board_size)
       self._lock = True
       self._root.after(10, self._engine_play_and_unlock)

    def quit(self):
        if self.is_engine_valid():
            self._engine.quit_and_shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--game",
                        type=str,
                        metavar="<game type>",
                        default="go",
                        help="One of go/gomok/nogo/othello")
    parser.add_argument("-b", "--boardsize",
                        type=int,
                        metavar="<int>",
                        default=0,
                        help="Select a specific board size.")
    parser.add_argument("-c", "--command",
                        type=str,
                        metavar="<string>",
                        default=None,
                        help="The command of GTP engine.")
    parser.add_argument("--engine-color",
                        type=str,
                        metavar="<string>",
                        default="black",
                        help="The color of GTP engine. Should be black/white.")
    args = parser.parse_args()
    gui = Gui(args)
    gui.quit()
