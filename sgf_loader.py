from gtp import GtpVertex, GtpColor
import random

class SgfLoader:
    def __init__(self, filename):
        self.history = list()
        self.black_player = str()
        self.white_player = str()
        self.board_size = None
        self.komi = None
        self._load(filename)

    def _process_key_value(self, key, val):
        def as_gtp_move(m, bsize=self.board_size):
            if len(m) == 0 or m == "tt":
                return GtpVertex("pass")
            x = ord(m[0]) - ord('a')
            y = ord(m[1]) - ord('a')
            y = bsize - 1 - y
            return GtpVertex((x,y))

        if key == "SZ":
            self.board_size = int(val)
        elif key == "KM":
            self.komi = float(val)
        elif key == "B":
            self.history.append((GtpColor(GtpColor.BLACK), as_gtp_move(val)))
        elif key == "W":
            self.history.append((GtpColor(GtpColor.WHITE), as_gtp_move(val)))
        elif key == "PB":
            self.black_player = val
        elif key == "PW":
            self.white_player = val
        elif key == "AB" or key == "AW":
            raise Exception("Do not support for AB/AW tag in the SGF file.")

    def _load(self, filename):
        try:
            with open(filename, "r") as f:
                sgf = f.read()
            self._parse(sgf)
            self._apply_symm()
        except Exception as err:
            print(err)

    def _parse(self, sgf):
        level = 0
        idx = 0
        node_cnt = 0
        key = str()
        while idx < len(sgf):
            c = sgf[idx]
            idx += 1;

            if c == '(':
                level += 1
            elif c == ')':
                level -= 1

            if c in ['(', ')', '\t', '\n', '\r'] or level != 1:
                continue
            elif c == ';':
                node_cnt += 1
            elif c == '[':
                end = sgf.find(']', idx)
                val = sgf[idx:end]
                self._process_key_value(key, val)
                key = str()
                idx = end+1
            else:
                key += c

    def _apply_symm(self):
        def move_symm(vtx, symm, bsize=self.board_size):
            if vtx.is_move():
                x, y = vtx.get()
                if symm & 4:
                    x, y = y, x
                if symm & 4:
                    x = bsize - 1 - x
                if symm & 4:
                    y = bsize - 1 - y
                vtx = GtpVertex((x,y))
            return vtx

        symm_history = list()
        symm = random.randint(0, 7)
        for c, vtx in self.history:
            vtx = move_symm(vtx, symm)
            symm_history.append((c, vtx))
        self.history, symm_history = symm_history, self.history

