import subprocess
import threading
import queue
import sys
import time

class GtpVertex:
    PASS_STR = "pass"
    RESIGN_STR = "resign"
    PASS_VERTEX = 100 * 100
    RESIGN_VERTEX = 100 * 100 + 1

    def __init__(self, val=None):
        self._vertex = None
        self.set(val)

    def set(self, val):
        if val is None:
            self._vertex = None
        elif isinstance(val, str):
            self._parse_str(val)
        elif isinstance(val, tuple) or isinstance(val, list):
            self._parse_coord(val)
        elif isinstance(val, int):
            if val == self.PASS_VERTEX or \
                   val == self.RESIGN_VERTEX:
                self._vertex = val
        else:
            raise Exception("Not a vertex data.")

    def _parse_coord(self, val):
        try:
            x, y = val
            if isinstance(x, int) and isinstance(y, int):
                self._vertex = (x, y)
            else:
                raise Exception("The coordinate is not integer.")
        except:
            raise Exception("Only accept for 2-dim coordinate.")

    def _parse_str(self, val):
        val = val.lower()

        if val == self.PASS_STR.lower():
            self._vertex = self.PASS_VERTEX
        elif val == self.RESIGN_STR.lower():
            self._vertex = self.RESIGN_VERTEX
        else:
            x = ord(val[0]) - ord('a')
            if x >= (ord('i') - ord('a')):
                x -= 1
            y = int(val[1:]) - 1
            self._vertex = (x, y)

    def _xy_to_vertex(self, x, y):
        if x >= 25 or x < 0 or y >= 25 or y < 0:
            raise Exception("Invalid vertex.")
        xstr = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
        return "{}{}".format(xstr[x], str(y+1))

    def is_pass(self):
        return str(self) == self.PASS_STR

    def is_resign(self):
        return str(self) == self.RESIGN_STR

    def is_move(self):
        return not self.is_pass() and \
                   not self.is_resign()

    def to_str(self):
        if self._vertex is None:
            raise Exception("None vertex.")

        if isinstance(self._vertex, int):
            if self._vertex == self.PASS_VERTEX:
                return self.PASS_STR
            return self.RESIGN_STR

        # must be the tuple
        x, y = self._vertex
        return self._xy_to_vertex(x,y)

    def __str__(self):
        return self.to_str()

    def get(self):
        return self._vertex

class Query:
    NORMAL = 1
    ANALYSIS = 2

    def __init__(self, gtp_command, query_type=NORMAL):
        self.type = query_type
        self.gtp_command = gtp_command
        self.result = None # = pr ? 
        self.response = list()

    def get_response(self):
        return self.response

    def get_main_command(self):
        buf = self.gtp_command.split()
        if buf is not None:
            return buf[0]
        return None

    def to_str(self):
        out = str()
        for line in self.response:
            out += ("{}\n".format(line))
        return out.strip()

    def __str__(self):
        return self.to_str()

class GTPEnginePipe:
    def __init__(self, args):
        self._engine = subprocess.Popen(
            args.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self._remaining = 0
        self._query_queue = queue.Queue()
        self._wait_queue = queue.Queue()
        self._finish_queue = queue.Queue()
        self._analysis_queue = queue.Queue()

        self._running = True
        self._send_query_thread = threading.Thread(
            target=self._send_query_loop, daemon=True
        )
        self._handle_gtp_thread = threading.Thread(
            target=self._handle_gtp_loop, daemon=True
        )
        self._read_err_thread   = threading.Thread(
            target=self._read_err_loop, daemon=True
        )

        for t in self._gather_threads():
            t.start()

    def _gather_threads(self):
        return [self._send_query_thread, self._handle_gtp_thread, self._read_err_thread]

    def is_running(self):
        return self._running

    def query_empty(self):
        return self._finish_queue.empty()

    def analysis_empty(self):
        return self._analysis_queue.empty()

    def push_query(self, query):
        self._remaining += 1
        try:
            self._query_queue.put(query)
        except queue.Full:
            self._remaining -= 1

    def push_gtp_command(self, cmd, query_type):
        query = Query(
            gtp_command="{}\n".format(cmd.strip()),
            query_type=query_type
        )
        self.push_query(query)

    def _read_err_loop(self):
        while self._running:
            try:
                line = self._engine.stderr.readline()
            except OSError as e:
                break
            sys.stderr.write(line)
            sys.stderr.flush()

    def _send_query_loop(self):
        while self._running:
            try:
                query = self._query_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            cmd = query.gtp_command

            try:
                self._engine.stdin.write(cmd)
                self._engine.stdin.flush()
                self._wait_queue.put(query)
            except OSError as e:
                break

    def _handle_gtp_loop(self):
        handling_query = None
        while self._running:
            if handling_query is None:
                try:
                    query = self._wait_queue.get(block=True, timeout=0.1)
                    handling_query = query
                except queue.Empty:
                    continue

            try:
                line = self._engine.stdout.readline().strip()
            except OSError as e:
                break

            if not line:
                if handling_query.type == Query.ANALYSIS:
                    self._analysis_queue.put({"type" : "end", "line" : None})
                self._finish_queue.put(handling_query)
                handling_query = None
                continue

            if line.split()[0] in ["=", "?"] and \
                   handling_query.result is None:
                handling_query.result = line.split()[0]
                line = line[1:].strip()

            if handling_query.type == Query.ANALYSIS and len(line) > 0:
                analysis_out = {"type" : "info", "line" : line}
                if "play" in line:
                    analysis_out["type"] = "play"
                self._analysis_queue.put(analysis_out)
            handling_query.response.append(line)

    def try_get_query(self, block=False):
        try:
            query = self._finish_queue.get(block=block, timeout=9999)
        except queue.Empty:
            return None
        self._remaining -= 1
        return query

    def try_get_response(self, block=False):
        query = self.try_get_query(block)
        if query is None:
            return None, None
        return query.result, str(query)

    def try_get_analysis(self, block=False):
        try:
            line = self._analysis_queue.get(block=block, timeout=9999)
        except queue.Empty:
            return None
        return line

    def pop_query(self):
        while not self.query_empty():
            self.try_get_query(True)

    def alive(self):
        return self._engine.poll() is None

    def wait(self):
        return self._engine.wait()

    def kill(self):
        return self._engine.kill()

    def wait_to_join(self):
        if not self._running:
            return

        self._running = False
        for t in self._gather_threads():
            t.join()

class GtpEngineBase:
    def __init__(self, args):
        self.args = args
        self._pipe = GTPEnginePipe(args)
        self._supported_list = [
            "list_commands"
        ]
        self._get_supported_commands()

    def __del__(self):
        self.shutdown()

    def _get_supported_commands(self):
        self._send_base("list_commands")

        while not self.query_empty():
            self.idle(0.1)
        res, val = self.get_last_response_raw()

        if res == "=":
            self._supported_list = val.strip().split()

    def _send_base(self, gtp_command, query_type=Query.NORMAL):
        if not self._pipe.is_running():
            raise Exception("Engine is stop.")

        if not isinstance(gtp_command, str):
            raise Exception("Not string type.")

        cmd_list = gtp_command.split()
        if len(cmd_list) == 0:
            raise Exception("String can not be empty.")

        if cmd_list[0] not in self._supported_list:
            raise Exception("Current command is not supported.")

        self._pipe.push_gtp_command(gtp_command, query_type)

    def idle(self, sec=1.0):
        # The queue/pipe may not update their status right now. Should
        # wait some time.
        time.sleep(sec)

    def send_command(self, val, query_type=Query.NORMAL):
        try:
            self._send_base(val, query_type)
        except Exception as err:
            sys.stderr.write("{}\n".format(str(err)))
            return False
        return True

    def support(self, val):
        return val in self._supported_list

    def pop_query(self):
        self._pipe.pop_query()

    def analysis_empty(self):
        return self._pipe.analysis_empty()

    def get_analysis_line(self):
        return self._pipe.try_get_analysis(True)

    def query_empty(self):
        return self._pipe.query_empty()

    def get_last_response_raw(self):
        return self._pipe.try_get_response(block=True)

    def get_last_response(self, raise_err=False):
        res, rep = self.get_last_response_raw()
        if raise_err and res == "?":
            raise Exception("Invalid command: ({}).".format(rep))
        return rep

    def get_last_query(self):
        return self._pipe.try_get_query(block=True)

    def shutdown(self):
        if self._pipe.alive():
            sys.stderr.write("Kill the GTP engine process. It is not the recommend way. Please enter \"quit\" before closing it.\n")
            self._pipe.kill()
            self._pipe.wait()
        self._pipe.wait_to_join()

class GtpEngine(GtpEngineBase):
    def __init__(self, args):
        super().__init__(args)

        self.analysis_type = None
        self.genmove_type = None
        self.raise_err = False
        self._self_check()

    def _self_check(self):
        if not self.support("name") or \
               not self.support("version") or \
               not self.support("protocol_version") or \
               not self.support("list_commands") or \
               not self.support("clear_board") or \
               not self.support("boardsize") or \
               not self.support("showboard") or \
               not self.support("komi") or \
               not self.support("play") or \
               not self.support("undo") or \
               not self.support("genmove") or \
               not self.support("quit"):
            raise Exception("It is a bad GTP engine")

    def return_response(self):
        return self.get_last_response(self.raise_err)

    def name(self):
        self.send_command("name")
        return self.return_response()

    def version(self):
        self.send_command("version")
        return self.return_response()

    def protocol_version(self):
        self.send_command("protocol_version")
        return self.return_response()

    def list_commands(self):
        self.send_command("list_commands")
        return self.return_response()

    def clear_board(self):
        self.send_command("clear_board")
        return self.return_response()

    def boardsize(self, bsize):
        self.send_command("boardsize {}".format(bsize))
        return self.return_response()

    def showboard(self):
        self.send_command("showboard")
        return self.return_response()

    def undo(self):
        self.send_command("undo")
        return self.return_response()

    def komi(self, komi):
        self.send_command("komi {}".format(komi))
        return self.return_response()

    def play(self, color, vertex):
        self.send_command("play {} {}".format(color, vertex))
        return self.return_response()

    def quit(self):
        self.send_command("quit")
        self.idle(0.1)

    def genmove(self, color):
        self.send_command("genmove {}".format(color))
        return self.return_response()

    def async_genmove(self, color):
        self.send_command("genmove {}".format(color))

if __name__ == '__main__':
    try:
        gnugo = GtpEngine("gnugo --mode gtp")

        print(gnugo.name())
        print(gnugo.version())
        print(gnugo.play("b", str(GtpVertex((1,2)))))
        print(str(GtpVertex((1,2))))
        print(gnugo.showboard())
        gnugo.quit()
        gnugo.shutdown()

    except Exception as err:
        sys.stderr.write("{}\n".format(str(err)))
