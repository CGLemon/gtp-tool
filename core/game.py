import copy

class Stone:
    BLACK = 0
    WHITE = 1
    EMPTY = 2
    INVLD = 3

    COLORS = [BLACK, WHITE]
    ALL = [BLACK, WHITE, EMPTY, INVLD]
    INVERT = [WHITE, BLACK, EMPTY, INVLD]
    SMAP = ["x", "o", ".",  "E"]

    @staticmethod
    def invert_color(c):
        if not c in Stone.ALL:
            raise Exception("Invalid game color.")
        return Stone.INVERT[c]

    @staticmethod
    def color_to_str(c):
        if not c in Stone.ALL:
            raise Exception("Invalid game color.")
        return Stone.SMAP[c]

class MailBoxGame:
    def __init__(self, board_size):
        self.board_size = board_size
        self.mailbox_size = board_size + 2
        self.num_intersections = self.board_size * self.board_size
        self.num_locations = self.mailbox_size * self.mailbox_size

        self.mailbox = [ Stone.INVLD ] * self.num_locations
        self.dir1 = [
            (1,0), (0,1), (-1,0), (0,-1) # for most games
        ]
        self.dir2 = [
            (1,1), (1,-1), (-1,1), (-1,-1) # for othello
        ]

    def play(self, x, y, color):
        raise NotImplementedError()

    def pass_legal(self):
        raise NotImplementedError()

    def play_pass(self):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    def legal(self, x, y, color):
        game = copy.deepcopy(self)
        try:
            game.play(x, y, color)
            return True
        except:
            pass
        return False

    def get_loc(self, x, y):
        return x + y * self.mailbox_size

    def reset(self):
        for i in range(self.num_locations):
            self.mailbox[i] = Stone.INVLD

        for y in range(self.board_size):
            for x in range(self.board_size):
                self.mailbox[self.get_loc(x, y)] = Stone.EMPTY

    def get_stone(self, x, y):
        return self.mailbox[self.get_loc(x, y)]

    def set_stone(self, x, y, c):
        if not c in Stone.ALL:
            raise Exception("Invalid game color.")
        self.mailbox[self.get_loc(x, y)] = c

class GoLikeGame(MailBoxGame):
    def __init__(self, board_size):
        super(GoLikeGame, self).__init__(board_size)
        super(GoLikeGame, self).reset()
        self.output_invert_y = True
        self.tomove = Stone.BLACK
        self.last_move = None

    def play(self, x, y, color):
        if not color in Stone.COLORS:
            raise Exception("Invalid play color.")

        if self.get_stone(x, y) != Stone.EMPTY:
            raise Exception("Play on the existed stone.")

        self.set_stone(x, y, color)
        self.tomove = Stone.invert_color(color)
        self.last_move = (x, y)

    def reset(self):
        super(GoLikeGame, self).reset()
        self.tomove = Stone.BLACK

    def __str__(self):
        def get_coordstr(size):
            coord = str()
            for x in range(size):
                xx = x
                if xx >= 8:
                    xx += 1
                coord += "{} ".format(chr(xx + ord('A')))
            return coord

        board = str()
        board += "   {}\n".format(get_coordstr(self.board_size))
        for y in range(self.board_size):
            yy = y
            if self.output_invert_y:
                yy = self.board_size - y - 1
            board += "{:2} ".format(yy+1)

            for x in range(self.board_size):
                xx = x
                c = self.get_stone(x, yy)
                board += "{} ".format(Stone.color_to_str(c))
            if self.board_size < 10:
                board = board[:-1]
            board += "{:2}".format(yy+1)
            board += "\n"
        board += "   {}\n".format(get_coordstr(self.board_size))
        return board

class GoGame(GoLikeGame):
    def __init__(self, board_size):
        super(GoGame, self).__init__(board_size)
        self.allow_capture = True
        self.pass_is_legal = True
        self.num_passes = 0

    def play(self, x, y, color):
        super(GoGame, self).play(x, y, color)

        for dx, dy in self.dir1:
            xx = x + dx
            yy = y + dy

            string, libs = self._get_string(xx, yy)
            if self.get_stone(xx, yy) == Stone.invert_color(color):
                if libs == 0:
                    if not self.allow_capture:
                        raise Exception("Don't allow the capture move.")
                    self._remove(string)
        _, libs = self._get_string(x, y)
        if libs == 0:
            raise Exception("Don't allow the suicide move.")
        self.num_passes = 0

    def play_pass(self):
        if self.pass_legal():
            self.tomove = Stone.invert_color(self.tomove)
            self.num_passes += 1
            self.last_move = None

    def pass_legal(self):
        if self.pass_is_legal:
            return True
        raise Exception("Pass is not a valid move.")

    def _get_string(self, x, y):
        color = self.get_stone(x, y)
        if not color in Stone.COLORS:
            return list(), 0

        string = list()
        libs = set()

        reached = { self.get_loc(x, y) }
        que = [ (x, y) ]

        while len(que) != 0:
            x, y = que.pop(0)
            string.append((x, y))

            for dx, dy in self.dir1:
               xx = x + dx
               yy = y + dy
               loc = self.get_loc(xx, yy)
               if self.get_stone(xx, yy) == color and not loc in reached:
                   reached.add(loc)
                   que.append((xx, yy))
               if self.get_stone(xx, yy) == Stone.EMPTY:
                   libs.add(loc)
        return string, len(libs)

    def _remove(self, string):
        for x, y in string:
           self.set_stone(x, y, Stone.EMPTY)

class NoGoGame(GoGame):
    def __init__(self, board_size):
        super(NoGoGame, self).__init__(board_size)
        self.allow_capture = False
        self.pass_is_legal = False

class GomokuGame(GoLikeGame):
    def __init__(self, board_size):
        super(GomokuGame, self).__init__(board_size)

class OthelloGame(GoLikeGame):
    def __init__(self, board_size):
        super(OthelloGame, self).__init__(board_size)
        self.output_invert_y = False
        midx = self.board_size // 2
        midy = self.board_size // 2
        self.init_positions = {
            Stone.BLACK: [(midx, midy-1), (midx-1, midy)],
            Stone.WHITE: [(midx-1, midy-1), (midx, midy)]
        }
        self.reset()

    def reset(self):
        super(OthelloGame, self).reset()
        for color, moves in self.init_positions.items():
            for x, y in moves:
                self.set_stone(x, y, color)

    def play(self, x, y, color):
        super(OthelloGame, self).play(x, y, color)
        self.all_dir = self.dir1 + self.dir2

        reversi_cnt = 0
        for dx, dy in self.all_dir:
            rayline = self._ray((x, y), (dx, dy))
            reversi_cnt += self._reversi(rayline, color)
        if reversi_cnt == 0:
            raise Exception("Invalid othello move.")

    def pass_legal(self):
        for y in range(self.board_size):
            for x in range(self.board_size):
                if self.legal(x, y, self.tomove):
                    return False
        return True

    def play_pass(self):
        if self.pass_legal():
            self.tomove = Stone.invert_color(self.tomove)

    def _ray(self, src, go):
        xx, yy = src
        dx, dy = go
        color = self.get_stone(xx, yy)

        rayline = list()
        if not color in Stone.COLORS:
            return list()
        xx += dx
        yy += dy
        while self.get_stone(xx, yy) == Stone.invert_color(color):
            rayline.append((xx, yy))
            xx += dx
            yy += dy
        if self.get_stone(xx, yy) == color:
            return rayline
        return list()

    def _reversi(self, rayline, color):
        reversi_cnt = 0
        for x, y in rayline:
            self.set_stone(x, y, color)
            reversi_cnt += 1
        return reversi_cnt

class HexLikeGame(MailBoxGame):
    pass

if __name__ == '__main__':
    game = GoGame(9)
    print(game)

    print(game.legal(2, 3, game.tomove))
    game.play(2, 3, game.tomove)
    print(game)
    game.reset()
    print(game.legal(2, 2, game.tomove))
    game.play(2, 2, game.tomove)
    print(game)
