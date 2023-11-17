import argparse
import random
import json
import hashlib
import glob, os
from datetime import datetime
from gtp import GtpVertex, GtpColor, GtpEngine
from sgf_loader import SgfLoader

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
    def __init__(self, args):
        existed_names = list()
        self._status = list()
        self._judge_gtp = None

        with open(args.engines, "r") as f:
            setting = json.load(f)

        for s in setting:
            try:
                if s["type"] == "judge":
                    self._judge_gtp = JudgeGtpEngine(s["command"])
                    print("Setup the GTP engine, {}, as judge.".format(s["name"]))
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
                        "name"      : s["name"],
                        "command"   : s["command"],
                        "elo"       : s["elo"],
                        "engine"    : e,
                        "black-WDL" : [0, 0, 0],
                        "white-WDL" : [0, 0, 0]
                    }
                )
                print("Setup the GTP engine, {}.".format(s["name"]))
            except Exception as err:
                print(err)

        if len(self._status) <= 1:
            self.shutdown()
            raise Exception("Only one/zero GTP engine. Please setup more engines.")
        if self._judge_gtp is None:
            self.shutdown()
            raise Exception("Need to setup judge engine.")
        self.board_size = args.boardsize
        self.komi = args.komi
        self.sgf_files = list()
        self.save_dir = args.save_dir

        if args.sgf_dir is not None:
            self.sgf_files.extend(glob.glob(os.path.join(args.sgf_dir, "*.sgf")))
        if self.save_dir is not None:
            path = self.save_dir
            if not os.path.isdir(path):
                os.makedirs(path)

    def show_match_result(self):
        self._status.sort(key=lambda s: s["name"])
        print("[ name ] -> [ black (W/D/L) ] [ white (W/D/L) ]")
        for s in self._status:
            name = s["name"]
            b_wdl = s["black-WDL"]
            w_wdl = s["white-WDL"]
            res = "{} -> ({}/{}/{}) ({}/{}/{})".format(
                      name, b_wdl[0], b_wdl[1], b_wdl[2], w_wdl[0], w_wdl[1], w_wdl[2])
            print(res)

    def _init_engines(self, black, white, judge):
        random.shuffle(self.sgf_files)
        loader = None
        while len(self.sgf_files) > 0:
            try:
                loader = SgfLoader(self.sgf_files[0])
                if loader.board_size != self.board_size:
                    raise Exception("The boardsize is incorrect.")
                break
            except Exception as err:
                sgf = self.sgf_files.pop(0)

        for e in [black, white, judge]:
            e.clear_board()
            e.boardsize(self.board_size)
            e.komi(self.komi)
            try:
                if loader is not None:
                    for c, vtx in loader.history:
                        e.play(str(c), str(vtx))
            except Exception as err:
                sgf = self.sgf_files.pop(0)
                self._init_engines(black, white, judge)
                break

    def _save_sgf(self, black, white, history, result):
        now = datetime.now()
        curr_time = now.strftime("%Y-%m-%d-%H:%M:%S")
        sgf = "(;GM[1]FF[4]SZ[{}]KM[{}]RU[unknown]PB[{}]PW[{}]DT[{}]".format(
                  self.board_size, self.komi, black["name"], white["name"], curr_time)
        if result is not None:
            sgf += "RE[{}]".format(result)
        for color, vertex in history:
            cstr = str(color).upper()[:1]

            if vertex.is_pass():
                vstr = "tt"
            elif vertex.is_resign():
                vstr = ""
            else:
                x, y = vertex.get()
                y = self.board_size - 1 - y
                vstr = str()
                vstr += chr(x + ord('a'))
                vstr += chr(y + ord('a'))
            sgf += ";{}[{}]".format(cstr, vstr)
        sgf += ")"

        if self.save_dir:
            sgf_name = "{}(B)_vs_{}(W)-{}.sgf".format(black["name"], white["name"], curr_time)
            sgf_path = os.path.join(self.save_dir, sgf_name)
            with open(sgf_path, "w") as f:
                f.write(sgf)

    def _sample_engines(self):
        random.shuffle(self._status)
        black = self._status.pop(0)
        white = self._status.pop(0)
        return black, white

    def play_game(self):
        black, white = self._sample_engines()
        history, result = list(), None

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
                result = "{}+Resign".format(str(c).upper()[:1])
                break

            rep = judge.is_legal(str(c), str(vtx))
            # 0 is illegal
            # 1 is legal 
            if int(rep) == 0:
                winner, loser = players[str(c.next())], players[str(c)]
                result = "{}+Illegal".format(str(c).upper()[:1])
                break

            if vtx.is_pass():
                num_passes += 1
            else:
                num_passes = 0

            try:
                next_player.play(str(c), str(vtx))
                judge.play(str(c), str(vtx))
                history.append((c, vtx))
            except Exception as err:
                print("Not a legal move.")
                break

            if num_passes >= 2:
                rep = judge.final_score()
                result = rep
                if "b+" in rep.lower():
                    winner, loser = black, white
                elif "w+" in rep.lower():
                    winner, loser = white, black
                break
            c = c.next()

        for e in gtp_players.values():
            e.clear_board()
            e.protocol_version() # interrupt ponder

        self._save_sgf(black, white, history, result)

        if winner is not None:
            if winner["name"] == black["name"]:
                winner["black-WDL"][0] += 1
                loser["white-WDL"][2] += 1
            else:
                winner["white-WDL"][0] += 1
                loser["black-WDL"][2] += 1
        else:
            black["black-WDL"][1] += 1
            white["white-WDL"][1] += 1

        self._status.extend([black, white])

    def shutdown(self):
        while len(self._status) > 0:
            s = self._status.pop(0)
            e = s["engine"]
            e.quit()
            e.shutdown()
            print("Quit the GTP engine: {}.".format(s["name"]))

        judge = self._judge_gtp
        judge.quit()
        judge.shutdown()
        print("Quit the judge engine.")

    def __del__(self):
        self.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--engines",
                        type=str,
                        metavar="<path-to-json>",
                        default=None,
                        help="The engines list setting.")
    parser.add_argument("--sgf-dir",
                        type=str,
                        metavar="<path-to-SGF>",
                        default=None,
                        help="Load the SGF file from here.")
    parser.add_argument("--save-dir",
                        type=str,
                        metavar="<save-path>",
                        default=None,
                        help="Save the SGF file here.")
    parser.add_argument("-b", "--boardsize",
                        type=int,
                        metavar="<int>",
                        default=19,
                        help="Play the match games with this board size.")
    parser.add_argument("-k", "--komi",
                        type=float,
                        metavar="<float>",
                        default=7.5,
                        help="Play the match games with this komi.")
    parser.add_argument("-g", "--num-games",
                        type=int,
                        metavar="<int>",
                        default=0,
                        help="The number of played games.")
    args = parser.parse_args()
    
    if args.engines is None:
        print("Please give the engines json file.")
        exit()

    m = MatchTool(args)
    for g in range(args.num_games):
        m.play_game()
        if (g+1) % 10 == 0:
            print("Played {} games.".format(g+1))
            m.show_match_result()
            print("")
    m.show_match_result()
    m.shutdown()
