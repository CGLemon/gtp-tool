import tkinter as tk
from functools import partial
from core.game import Stone

class GoLikeBoardUilts:

    @staticmethod
    def draw_black(canvas, grid_size, x, y):
        radius = max(grid_size/2 - 2, 15)
        border = max(round(radius/15), 2)
        lower = grid_size / 2
        xx = lower + x * grid_size
        yy = lower + y * grid_size
        canvas.create_oval(
            xx-radius, yy-radius, xx+radius, yy+radius,
            fill="black", outline="#696969", width=border)

    @staticmethod
    def draw_white(canvas, grid_size, x, y):
        radius = max(grid_size/2 - 2, 15)
        border = max(round(radius/15), 2)
        lower = grid_size / 2
        xx = lower + x * grid_size
        yy = lower + y * grid_size
        canvas.create_oval(
            xx-radius, yy-radius, xx+radius, yy+radius,
            fill="white", outline="black", width=border)

    @staticmethod
    def draw_star(canvas, grid_size, x, y):
        radius = 2
        border = 0
        lower = grid_size / 2
        xx = lower + x * grid_size
        yy = lower + y * grid_size
        canvas.create_oval(
            xx-radius, yy-radius, xx+radius, yy+radius,
            fill="black", outline="black", width=border)

    @staticmethod
    def draw_legal(canvas, grid_size, x, y):
        radius = max(grid_size/10 - 2, 4)
        border = 0
        lower = grid_size / 2
        xx = lower + x * grid_size
        yy = lower + y * grid_size
        canvas.create_oval(
            xx-radius, yy-radius, xx+radius, yy+radius,
            fill="yellow", outline="yellow", width=border)

    @staticmethod
    def draw_illegal(canvas, grid_size, x, y):
        radius = max(grid_size/10 - 2, 4)
        border = 0
        lower = grid_size / 2
        xx = lower + x * grid_size
        yy = lower + y * grid_size
        canvas.create_oval(
            xx-radius, yy-radius, xx+radius, yy+radius,
            fill="red", outline="red", width=border)

class BoardCanvas:
    BLACK = Stone.BLACK
    WHITE = Stone.WHITE
    EMPTY = Stone.EMPTY
    INVLD = Stone.INVLD

    LEGAL = 0
    ILLEGAL = 1
    LASTMOVE = 2
    STAR = 3
    NOHINT = 4

    def __init__(self, root, board_size, canvas_size):
        self.root = root
        self.board_size = board_size
        self.canvas_size = canvas_size
        self.grid_size = canvas_size / self.board_size
        self.num_grids = board_size * board_size
        self.boardbuf = [BoardCanvas.INVLD] * self.num_grids
        self.hintbuf = [BoardCanvas.NOHINT] * self.num_grids

    def bind_wrapper(self, func):
        raise NotImplementedError()

    def sync(self, game):
        raise NotImplementedError()

    def render(self):
        raise NotImplementedError()

    def sethint(self, x, y, hint):
        self.hintbuf[x + y * self.board_size] = hint

class GoLikeBoard(BoardCanvas):
    def __init__(self, root, board_size, canvas_size):
        super(GoLikeBoard, self).__init__(root, board_size, canvas_size)
        self.canvas = tk.Canvas(
            self.root,
            width=self.board_size * self.grid_size,
            height=self.board_size * self.grid_size,
            bg="#CD853F")
        self.canvas.place(x=0, y=0)

    def bind_wrapper(self, func):
        def transfer_coord(board_size, grid_size, event):
            lower = grid_size / 2
            x = round((event.x - lower)/grid_size)
            y = round((event.y - lower)/grid_size)
            func(x, board_size-y-1)
        self.canvas.bind("<Button-1>", partial(transfer_coord, self.board_size, self.grid_size))

    def sync(self, game):
        def is_star(x, y, size):
            point = x + y * size

            stars = [0] * 3
            points = [0] * 2
            hits = 0
            if size % 2 == 0 or size < 9:
                return False
            stars[0] = 3 if size >= 13 else 2
            stars[1] = size // 2;
            stars[2] = size - 1 - stars[0]

            points[0] = point // size;
            points[1] = point % size;

            for i in points:
                for j in stars:
                    if i == j:
                        hits += 1
            return hits >= 2

        for y in range(self.board_size):
            for x in range(self.board_size):
                idx = x + y * self.board_size
                self.boardbuf[idx] = game.get_stone(x, y)
                self.hintbuf[idx] = BoardCanvas.NOHINT
                if is_star(x, y, self.board_size):
                    self.hintbuf[idx] = BoardCanvas.STAR

    def render(self):
        self.canvas.delete("all")

        lower = self.grid_size / 2
        upper = self.grid_size * self.board_size - self.grid_size / 2
        for i in range(self.board_size):
            offset = i * self.grid_size
            self.canvas.create_line(lower       , lower+offset, upper       , lower+offset)
            self.canvas.create_line(lower+offset, lower       , lower+offset, upper)

        blackoval = partial(GoLikeBoardUilts.draw_black, self.canvas, self.grid_size)
        whiteoval = partial(GoLikeBoardUilts.draw_white, self.canvas, self.grid_size)
        staroval = partial(GoLikeBoardUilts.draw_star, self.canvas, self.grid_size)
        illegaloval = partial(GoLikeBoardUilts.draw_illegal, self.canvas, self.grid_size)

        for y in range(self.board_size):
            for x in range(self.board_size):
                idx = x + (self.board_size-y-1) * self.board_size
                color = self.boardbuf[idx]
                hint = self.hintbuf[idx]
                if color == BoardCanvas.BLACK:
                    blackoval(x, y)
                if color == BoardCanvas.WHITE:
                    whiteoval(x, y)
                if color == BoardCanvas.EMPTY and hint == BoardCanvas.STAR:
                    staroval(x, y)
                if hint == BoardCanvas.ILLEGAL:
                    illegaloval(x, y)

class OthelloLikeBoard(BoardCanvas):
    def __init__(self, root, board_size, canvas_size):
        super(OthelloLikeBoard, self).__init__(root, board_size, canvas_size)
        self.canvas = tk.Canvas(
            self.root,
            width=self.board_size * self.grid_size,
            height=self.board_size * self.grid_size,
            bg="green")
        self.canvas.place(x=0, y=0)

    def bind_wrapper(self, func):
        def transfer_coord(grid_size, event):
            lower = 0.0
            x = int((event.x - lower)/grid_size)
            y = int((event.y - lower)/grid_size)
            func(x, y)
        self.canvas.bind("<Button-1>", partial(transfer_coord, self.grid_size))

    def sync(self, game):
        for y in range(self.board_size):
            for x in range(self.board_size):
                idx = x + y * self.board_size
                self.boardbuf[idx] = game.get_stone(x, y)
                self.hintbuf[idx] = BoardCanvas.NOHINT
                if game.legal(x, y, game.tomove):
                    self.hintbuf[idx] = BoardCanvas.LEGAL

    def render(self):
        self.canvas.delete("all")

        lower = 0
        upper = self.grid_size * self.board_size
        for i in range(self.board_size+1):
            offset = i * self.grid_size
            self.canvas.create_line(lower       , lower+offset, upper       , lower+offset)
            self.canvas.create_line(lower+offset, lower       , lower+offset, upper)

        blackoval = partial(GoLikeBoardUilts.draw_black, self.canvas, self.grid_size)
        whiteoval = partial(GoLikeBoardUilts.draw_white, self.canvas, self.grid_size)
        legaloval = partial(GoLikeBoardUilts.draw_legal, self.canvas, self.grid_size)

        for y in range(self.board_size):
            for x in range(self.board_size):
                idx = x + y * self.board_size
                color = self.boardbuf[x + y * self.board_size]
                hint = self.hintbuf[idx]
                if color == BoardCanvas.BLACK:
                    blackoval(x, y)
                if color == BoardCanvas.WHITE:
                    whiteoval(x, y)
                if color == BoardCanvas.EMPTY and hint == BoardCanvas.LEGAL:
                    legaloval(x, y)

class HexBoard(BoardCanvas):
    def __init__(self, root, board_size, grid_size):
        super(HexBoard, self).__init__(root, board_size, grid_size)