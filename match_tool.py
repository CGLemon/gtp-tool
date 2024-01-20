import argparse
import random
import json
import hashlib
import glob, os
import math
import select, sys
from datetime import datetime
from gtp import GtpVertex, GtpColor, GtpEngine
from sgf_loader import SgfLoader
from elo import Elo

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

    def quit_and_shutdown(self):
        self.quit()
        self.shutdown()

class LazyGtpEngine(GtpEngine):
    def __init__(self, command):
        super().__init__(command)
        self._ready = True

    def wakeup(self):
        if self._ready:
            return
        self.setup()
        self._ready = True

    def sleep(self):
        if not self._ready:
            return
        self.quit()
        self.shutdown()
        self._ready = False

    def quit_and_shutdown(self):
        self.sleep()

class DefaultGtpEngine(GtpEngine):
    def __init__(self, command):
        super().__init__(command)

    def quit_and_shutdown(self):
        self.quit()
        self.shutdown()

class MatchTool:
    def __init__(self, args):
        existed_names = list()
        self._status = list()
        self._judge_gtp = None
        self._fixed_elo = None
        self._fixed_name = None

        with open(args.engines, "r") as f:
            setting = json.load(f)

        for s in setting:
            try:
                engine_types = s["type"].split('-')
                if "skip" in engine_types:
                    continue
                if "judge" in engine_types:
                    self._judge_gtp = JudgeGtpEngine(s["command"])
                    print("Setup the GTP engine, {}, as judge.".format(s["name"]))
                    continue
                ori_name = s["name"]
                while s["name"] in existed_names:
                    sha = hashlib.sha256()
                    sha.update(s["name"].encode())
                    s["name"] = "{}-{}".format(ori_name, sha.hexdigest()[:6])
                if "fixed" in engine_types:
                    if self._fixed_name is None:
                        self._fixed_name = s["name"]
                        self._fixed_elo = s["elo"]
                    else:
                        print("Only accept one fixed Elo engine. Please remove redundant fixed label.")
                if "lazy" in engine_types:
                    e = LazyGtpEngine(s["command"])
                else:
                    e = DefaultGtpEngine(s["command"])
                e.raise_err = True
                e.protocol_version()
                existed_names.append(s["name"])

                self._status.append(
                    {
                        "name"      : s["name"],
                        "command"   : s["command"],
                        "elo"       : Elo(s["elo"], 40.),
                        "engine"    : e,
                        "black-WDL" : [0, 0, 0],
                        "white-WDL" : [0, 0, 0],
                        "games"     : 0
                    }
                )
                print("Setup the GTP engine, {}.".format(s["name"]))
                if type(e) == LazyGtpEngine:
                    e.sleep()
            except Exception as err:
                print(err)

        if len(self._status) <= 1:
            self.shutdown()
            raise Exception("Only one/zero GTP engine. Please setup more engines.")
        if self._judge_gtp is None:
            self.shutdown()
            raise Exception("Need to setup judge engine.")
        self.played_games = 0
        self.board_size = args.boardsize
        self.komi = args.komi
        self.sample_rate = min(max(args.sample_rate, 0.0), 1.0)
        self.sgf_files = list()
        self.save_dir = args.save_dir
        self.k_decay_factor = max(args.k_decay_factor, 1.)
        self.start_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

        if args.sgf_dir is not None:
            self.sgf_files.extend(glob.glob(os.path.join(args.sgf_dir, "*.sgf")))
        if self.save_dir is not None:
            path = self.save_dir
            if not os.path.isdir(path):
                os.makedirs(path)    

        info = str()
        info += "Board Size: {}\n".format(self.board_size)
        info += "Komi: {}\n".format(self.komi)
        if args.sgf_dir is not None and self.sample_rate > 0:
            info += "Load the SGF files from {}.\n".format(
                        args.sgf_dir)
        if self.save_dir is not None:
            info += "Save the SGF files to {}.\n".format(
                        self.save_dir)
            info += "Save the current result to {}.\n".format(
                        self._get_result_txt_name())
        print(info, end="")

    def print_match_result(self):
        print(self._get_match_result_str())

    def _init_engines(self, black, white, judge):
        def roulette(self, prob):
            r = random.random()
            return r < prob

        for e in [black, white]:
            if type(e) == LazyGtpEngine:
                e.wakeup();

        random.shuffle(self.sgf_files)
        loader = None
        history = list()
        curr_color = GtpColor(GtpColor.BLACK)
        while len(self.sgf_files) > 0 and roulette(self.sample_rate):
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
                    history = loader.history
                    for c, vtx in loader.history:
                        e.play(str(c), str(vtx))
            except Exception as err:
                sgf = self.sgf_files.pop(0)
                return self._init_engines(black, white, judge)
        if len(history) > 0:
            c, _ = history[-1]
            curr_color = c.next()
        return history, curr_color

    def _save_sgf(self, black, white, history, result):
        curr_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
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

    def _get_result_txt_name(self):
        filename = "result-{}.txt".format(self.start_time)
        return os.path.join(self.save_dir, filename)

    def _save_match_result(self):
        res = self._get_match_result_str()
        with open(self._get_result_txt_name(), "w") as f:
            f.write(res)

    def _sample_engines(self):
        def random_select_by_elo(status, key_fn):
            status.sort(key=lambda s: s["elo"].get())
            curr_elo = p1["elo"].get()
            accm = 0

            for s in status:
                diff = abs(curr_elo - s["elo"].get())
                accm += key_fn(diff)
            select = random.random() * accm

            accm = 0
            for idx, s in enumerate(status):
                diff = abs(curr_elo - s["elo"].get())
                accm += key_fn(diff)
                if accm > select:
                    return idx
            return -1

        self._status.sort(key=lambda s: s["games"])
        p1 = self._status.pop(0)
        idx = random_select_by_elo(
                  self._status,
                  lambda v: 1.0 / (1.0 + pow(10.0, v / 100.0))
              )
        p2 = self._status.pop(idx)

        shuflist = [p1, p2]
        random.shuffle(shuflist)
        black = shuflist[0]
        white = shuflist[1]
        return black, white

    def _get_match_result_str(self):
        self._status.sort(key=lambda s: s["elo"].get(), reverse=True)
        out = str()
        out += "[ name ] : [ Elo ] -> [ black (W/D/L) ] [ white (W/D/L) ]"
        for s in self._status:
            name = s["name"]
            elo = s["elo"]
            b_wdl = s["black-WDL"]
            w_wdl = s["white-WDL"]
            out += "\n{} : {} -> ({}/{}/{}) ({}/{}/{})".format(
                       name, elo, b_wdl[0], b_wdl[1], b_wdl[2], w_wdl[0], w_wdl[1], w_wdl[2])
        return out

    def _finish_and_update(self, winner, loser, black, white):
        if winner is not None:
            if winner["name"] == black["name"]:
                winner["black-WDL"][0] += 1
                loser["white-WDL"][2] += 1
            else:
                winner["white-WDL"][0] += 1
                loser["black-WDL"][2] += 1
            winner["elo"].beat(loser["elo"])
        else:
            black["black-WDL"][1] += 1
            white["white-WDL"][1] += 1
            black["elo"].draw(white["elo"])

        for p in [black, white]:
            p["games"] += 1
            k = p["elo"].get_k()
            if k != 0.:
                k_lambda = 0.69314718056/self.k_decay_factor
                if k < 16:
                    k_lambda /= 2.
                k = k * math.exp(-k_lambda)
                k = max(k, 5)
                p["elo"].set_k(k)
            if type(p["engine"]) == LazyGtpEngine:
                p["engine"].sleep()
        self._status.extend([black, white])
        self.played_games += 1

        if self._fixed_name is not None:
            offset_elo = 0
            self._status 
            for s in self._status:
               if s["name"] == self._fixed_name:
                   offset_elo = self._fixed_elo - s["elo"].get()
            for s in self._status:
                s["elo"].set(s["elo"].get() + offset_elo)

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
        history, c = self._init_engines(black["engine"], white["engine"], judge)

        num_passes = 0;
        winner, loser = None, None

        while True:
            curr_player = gtp_players[str(c)]
            next_player = gtp_players[str(c.next())]

            vtx = GtpVertex(curr_player.genmove(str(c)))

            if vtx.is_resign():
                winner, loser = players[str(c.next())], players[str(c)]
                result = "{}+Resign".format(str(c.next()).upper()[:1])
                break

            rep = judge.is_legal(str(c), str(vtx))
            # 0 is illegal
            # 1 is legal
            if int(rep) == 0:
                winner, loser = players[str(c.next())], players[str(c)]
                result = "{}+Illegal".format(str(c.next()).upper()[:1])
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
        self._finish_and_update(winner, loser, black, white)
        self._save_match_result()

    def shutdown(self):
        while len(self._status) > 0:
            s = self._status.pop(0)
            e = s["engine"].quit_and_shutdown()
            print("Quit the GTP engine: {}.".format(s["name"]))
        if self._judge_gtp is not None:
            self._judge_gtp.quit_and_shutdown()
            self._judge_gtp = None
            print("Quit the judge engine.")

    def __del__(self):
        self.shutdown()

def match_loop():
    info = str()
    info += "Start the match loop...\n"
    info += "Please enter the following commands to control the loop,\n"
    info += "\tquit: stop the match loop\n"
    info += "\tshow: print the current result\n"
    print(info, end="")

    m = MatchTool(args)
    while True:
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if rlist:
            line = sys.stdin.readline().strip()
            if line == "stop":
                break
            elif line == "show":
                m.print_match_result()
            else:
                print("Unknown command.")
        m.play_game()
        if m.played_games % 100 == 0:
            print("Played {} games.".format(m.played_games))
    m.shutdown()
    print("Finished...")

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
    parser.add_argument("-s", "--sample-rate",
                        type=float,
                        metavar="<0.0 ~ 1.0>",
                        default=0.5,
                        help="The probability to start from SGF file.")
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
    parser.add_argument("--k-decay-factor",
                        type=float,
                        metavar="<float>",
                        default=25,
                        help="Halve the K factor after playing factor games.")
    args = parser.parse_args()

    if args.engines is None:
        print("Please give the engines json file.")
        exit()
    match_loop()
