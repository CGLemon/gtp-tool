from gtp import GtpVertex, GtpColor

class SgfLoader:
    def __init__(self, filename):
        self.history = list()
        self.board_size = None
        self.komi = None
        self._load(filename)

    def _process_key_value(self, key, val):
        def as_gtp_move(m, size=self.board_size):
            if len(m) == 0 or m == "tt":
                return GtpVertex("pass")
            x = ord(m[0]) - ord('a')
            y = ord(m[0]) - ord('a')
            y = size - 1 - y
            return GtpVertex((x,y))

        if key == "SZ":
            self.board_size = int(val)
        elif key == "KM":
            self.komi = float(val)
        elif key == "B":
            self.history.append((GtpColor(GtpColor.BLACK), as_gtp_move(val)))
        elif key == "W":
            self.history.append((GtpColor(GtpColor.WHITE), as_gtp_move(val)))
        elif key == "AB" or key == "AW":
            raise Exception("Do not support for AB/Aw tag in the SGF file.")

    def _load(self, filename):
        try:
            with open(filename, "r") as f:
                sgf = f.read()
            self._parse(sgf)
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
