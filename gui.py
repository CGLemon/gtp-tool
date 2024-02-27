import sys
import argparse
import core.game as game
import core.render_helper as render
import tkinter as tk
import tkinter.font as font
from functools import partial
from core.gtp import GtpVertex, GtpColor, GtpEngine

class Gui():
    def __init__(self, args):
        self.game_type = args.game.lower()
        self.board_size = args.boardsize
        self._engine = GtpEngine("gnugo --mode gtp")

        self.width = 1200
        self.height = 900

        self._root = tk.Tk()
        self._root.resizable(True, True)
        self._root.title("GUI")
        self._root.geometry("{w}x{h}".format(w=self.width, h=self.height))

        self._frames = list()
        self._init_layout()
        self._render()
        self._root.after(0, self.engine_loop)
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
        self._destroy()
        self._init_layout()

    def _play_pass(self):
        if self._game.pass_legal():
            self._game.play_pass()
        else:
            sys.stderr.write("Pass is not legal move.\n")

    def _play_at(self, x, y):
        self.board_canvas.sync(self._game)
        if self._game.legal(x, y, self._game.tomove):
            self._game.play(x, y, self._game.tomove)
            self._render()
        else:
           self.board_canvas.sethint(x, y, render.BoardCanvas.ILLEGAL)
           self.board_canvas.render()
           sys.stderr.write("The {}-{} is not legal move.\n".format(x, y))

    def _render(self):
        self.board_canvas.sync(self._game)
        self.board_canvas.render()

    def engine_loop(self):
        print("loop")

        self._root.after(1000, self.engine_loop)

    def quit(self):
        self._engine.quit()
        self._engine.shutdown()

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
    args = parser.parse_args()
    gui = Gui(args)
    gui.quit()

