from gtp import GtpEngine, GtpVertex
from collections import OrderedDict
import json

BOARD_SIZE = 8
KOMI = 1.5

def json_input():
    raw = input()
    obj = json.loads(raw, object_pairs_hook=OrderedDict)
    return OrderedDict(obj)

def json_output(obj):
    raw = json.dumps(obj)
    print(raw)

def recover_from_input(engine, requests, responses):
    engine.boardsize(BOARD_SIZE)
    engine.komi(KOMI)

    movelist = []
    num_turn = len(responses)

    for i in range(num_turn):
        x, y = requests[i]["x"], requests[i]["y"]
        if not(x == -2 and y == -2):
            movelist.append([x, y])

        x, y = responses[i]["x"], responses[i]["y"]
        movelist.append([x, y])

    x, y = requests[num_turn]["x"], requests[num_turn]["y"]
    if not(x == -2 and y == -2):
        movelist.append([x, y])

    color_map = ["b", "w"]
    curr_color = "b"
    for i, (x, y) in enumerate(movelist):
        if x == -1 and y == -1:
            vtx = GtpVertex("pass")
        else:
            vtx = GtpVertex((x-1, y-1))
        engine.play(curr_color, str(vtx))
        curr_color = color_map[(i+1)%2]
    return curr_color

def think_move(engine, requests, responses):
    curr_color = recover_from_input(engine, requests, responses)
    move = GtpVertex(engine.genmove(curr_color))

    response = {}
    if move.is_pass() or move.is_resign():
        response["x"] = response["y"] = -1
    else:
        x, y = move.get()
        response["x"] = x+1
        response["y"] = y+1
    json_output({"response": response})

if __name__ == "__main__":
    raw = json_input()
    requests, responses = raw["requests"], raw["responses"]

    e = GtpEngine("gnugo --mode gtp")
    think_move(e, requests, responses)
    e.quit()
    e.shutdown()
