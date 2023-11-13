import argparse
import random
import json
import hashlib
import glob, os
from gtp import GtpVertex, GtpColor, GtpEngine

class JudgeGtpEngine(GtpEngine):
    EXTENDED_SUPPORTED_LIST = [
        "final_score",
        "is_legal"
    ]

    def __init__(self, command):
        super().__init__(command)
        self._judge_check()

    def _judge_check(self):
        for c in self.EXTENDED_SUPPORTED_LIST:
            if not self.support(c):
                raise Exception("Need to support for GTP command: {}.".format(c))

    def final_score(self):
        self.send_command("final_score")
        return self.return_response()

    def is_legal(self, color, vertex):
        self.send_command("is_legal {} {}".format(color, vertex))
        return self.return_response()

class MatchTool:
    def __init__(self, args, setting):
        existed_names = list()
        self._status = list()
        self._judge_gtp = None

        for s in setting:
            try:
                if s["type"] == "judge":
                    self._judge_gtp = JudgeGtpEngine(s["command"])
                    print("Launch the GTP engine: {}.".format(s["name"]))
                    continue
                ori_name = s["name"]
                while s["name"] in existed_names:
                    sha = hashlib.sha256()
                    sha.update(s["name"].encode())
                    s["name"] = "{}-{}".format(ori_name, sha.hexdigest()[:6])
                e = GtpEngine(s["command"])
                e.raise_err = True
                e.protocol_version()
                existed_names.append(s["name"])
                self._status.append(
                    {
                        "name"          : s["name"],
                        "command"       : s["command"],
                        "elo"           : s["elo"],
                        "engine"        : e,
                        "win-draw-lose" : [0, 0, 0]
                    }
                )
                print("Launch the GTP engine: {}.".format(s["name"]))
            except Exception as err:
                print(err)

        if len(self._status) <= 1:
            self.shutdown()
            raise Exception("Only one/zero GTP engine. Please launch more engines.")

        self.board_size = args.boardsize
        self.komi = args.komi
        self.sgf_files = list()

        if args.sgf_dir is not None:
            self.sgf_files.extend(glob.glob(os.path.join(args.sgf_dir, "*.sgf")))

    def show_match_result(self):
        for s in self._status:
            name = s["name"]
            wdl = s["win-draw-lose"]
            res = "{} -> (W/D/L)({}/{}/{})".format(name, wdl[0], wdl[1], wdl[2])
            print(res)

    def _init_engines(self, black, white, judge):
        for e in [black, white, judge]:
            e.clear_board()
            e.boardsize(self.board_size)
            e.komi(self.komi)
            if len(self.sgf_files) > 0:
                random.shuffle(self.sgf_files)
                try:
                    e.loadsgf(self.sgf_files[0])
                except Exception as err:
                    sgf = self.sgf_files.pop(0)
                    e.clear_board()
                    e.boardsize(self.board_size)
                    e.komi(self.komi)
                    print("Can not load the SGF file: {}".format(sgf))

    def play_game(self):
        random.shuffle(self._status)
        black = self._status.pop(0)
        white = self._status.pop(0)

        players = {
            str(GtpColor(GtpColor.BLACK)) : black,
            str(GtpColor(GtpColor.WHITE)) : white
        }
        gtp_players = {
            str(GtpColor(GtpColor.BLACK)) : black["engine"],
            str(GtpColor(GtpColor.WHITE)) : white["engine"]
        }
        judge = self._judge_gtp

        self._init_engines(black["engine"], white["engine"], judge)

        num_passes = 0;
        c = GtpColor(GtpColor.BLACK)
        winner, loser = None, None

        while True:
            curr_player = gtp_players[str(c)]
            next_player = gtp_players[str(c.next())]

            vtx = GtpVertex(curr_player.genmove(str(c)))

            if vtx.is_resign():
                winner, loser = players[str(c.next())], players[str(c)]
                break

            if judge is not None:
                 rep = judge.is_legal(str(c), str(vtx))
                 # 0 is illegal
                 # 1 is legal 
                 if int(rep) == 0:
                     winner, loser = players[str(c.next())], players[str(c)]
                     break

            if vtx.is_pass():
                num_passes += 1
            else:
                num_passes = 0

            try:
                next_player.play(str(c), str(vtx))
                if judge is not None:
                    judge.play(str(c), str(vtx))
            except Exception as err:
                print("Not a legal move.")
                break

            if num_passes >= 2:
                if judge is not None:
                    rep = judge.final_score()
                    if "b+" in rep.lower():
                        winner, loser = black, white
                    elif "w+" in rep.lower():
                        winner, loser = white, black
                break
            c = c.next()

        for e in gtp_players.values():
            e.clear_board()
            e.protocol_version() # interrupt ponder

        if winner is not None:
            winner["win-draw-lose"][0] += 1
            loser["win-draw-lose"][2] += 1
        else:
            black["win-draw-lose"][1] += 1
            white["win-draw-lose"][1] += 1
        self._status.append(black)
        self._status.append(white)
        random.shuffle(self._status)
        print("game over")

    def shutdown(self):
        while len(self._status) > 0:
            s = self._status.pop(0)
            e = s["engine"]
            e.quit()
            e.shutdown()
            print("Quit the GTP engine: {}.".format(s["name"]))

        judge = self._judge_gtp
        if judge is not None:
            judge.quit()
            judge.shutdown()
            print("Quit the judge engine.")

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
                        metavar="<path-to-json>",
                        default=None,
                        help="The engines list setting.")
    parser.add_argument("-s", "--sgf-dir",
                        type=str,
                        metavar="<path-to-SGF>",
                        default=None,
                        help="")
    parser.add_argument("-b", "--boardsize",
                        type=int,
                        metavar="<int>",
                        default=9,
                        help="")
    parser.add_argument("-k", "--komi",
                        type=float,
                        metavar="<float>",
                        default=7.0,
                        help="")

    args = parser.parse_args()
    if args.engines is None:
        print("Please give the engines json file.")
        exit()
    setting = load_json(args.engines)

    m = MatchTool(args, setting)
    for _ in range(2):
        m.play_game()
        m.show_match_result()
    m.shutdown()
