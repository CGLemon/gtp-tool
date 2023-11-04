import argparse
import random
import json
import hashlib
from gtp import GtpVertex, GtpColor, GtpEngine

class MatchTool:
    def __init__(self, args, setting):
        self._gtp_engines = dict()
        self._status = list()

        for s in setting:
            try:
                ori_name = s["name"]
                while s["name"] in self._gtp_engines.keys():
                    sha = hashlib.sha256()
                    sha.update(s["name"].encode())
                    s["name"] = "{}-{}".format(ori_name, sha.hexdigest()[:6])
                e = GtpEngine(s["command"])
                e.raise_err = True
                e.protocol_version()
                self._gtp_engines[s["name"]] = e
                self._status.append(
                    {
                        "name"          : s["name"],
                        "command"       : s["command"],
                        "elo"           : s["default elo"],
                        "win-draw-lose" : [0, 0, 0]
                    }
                )
                print("Launch the GTP engine: {}.".format(s["name"]))
            except Exception as err:
                print(err)

        if len(self._gtp_engines) <= 1:
            self.shutdown()
            raise Exception("Only one/zero GTP engine. Please launch more engines.")

        self.board_size = args.boardsize
        self.komi = args.komi

    def play_game(self):
        random.shuffle(self._status)
        black = self._status.pop(0)
        white = self._status.pop(0)

        players = [
            black, white
        ]
        gtp_players = {
            str(GtpColor(GtpColor.BLACK)) : self._gtp_engines[black["name"]],
            str(GtpColor(GtpColor.WHITE)) : self._gtp_engines[white["name"]],
        }

        for e in gtp_players.values():
            e.clear_board()
            e.boardsize(self.board_size)
            e.komi(self.komi)

        num_passes = 0;
        c = GtpColor(GtpColor.BLACK)

        while True:
            cur_player = gtp_players[str(c)]
            opp_player = gtp_players[str(c.next())]

            vtx = cur_player.genmove(str(c))
            vtx = GtpVertex(vtx)

            if vtx.is_pass():
                num_passes += 1
                if num_passes >= 2:
                    break
            else:
                num_passes = 0

            if vtx.is_resign():
                break
            try:
                opp_player.play(str(c), str(vtx))
            except Exception as err:
                print("Not a legal move.")
                break
            c = c.next()
        self._status.append(black)
        self._status.append(white)
        random.shuffle(self._status)
        print("game over")

    def shutdown(self):
        while len(self._status) > 0:
            s = self._status.pop(0)
            e = self._gtp_engines.pop(s["name"])
            e.quit()
            e.shutdown()
            print("Quit the GTP engine: {}.".format(s["name"]))

    def __del__(self):
        self.shutdown()

def load_json(name):
    with open(name, "r") as f:
        data = json.load(f)
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--engines",
                        type=str,
                        default=None,
                        help="The engines list setting.")
    parser.add_argument("-b", "--boardsize",
                        type=int,
                        default=9,
                        help="")
    parser.add_argument("-k", "--komi",
                        type=float,
                        default=7.0,
                        help="")
    args = parser.parse_args()
    if args.engines is None:
        print("Please give the engines json file.")
        exit()
    setting = load_json(args.engines)

    m = MatchTool(args, setting)
    m.play_game()
    m.shutdown()
