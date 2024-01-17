# gtp-tool

A pure python tool for GTP engine.

## Match

In recent years, the computer Go engine is significantly stronger than before. Two strong engines will prefer to play the same opening. The opening will affect the result. The main point for this tool is instead of GoGui. It can sample the SGF from the prepared SGF files.

First we need a judge engine, such as GNU Go. We do not implement any rule for this tool. The judge engine helps us to judge the legal move and compute the final score. For Ubuntu user, you can download it via apt packet.

```
$sudo apt install gnugo
```

Then set up the configure for each engine. Fill the following data for each item.

* ```name```: The engine name.
* ```command```: Command to run the engine.
* ```type```: The engine type labels. Yon can connect two labels by dash, e.g. ```fixed-lazy```.
    * ```judge```: The game judge. This engine must support ```final_score``` and ```is_legal``` command.
    * ```player```: Normal player.
    * ```fixed```: Fix the Elo rating.
    * ```lazy```: Will load engine when starting the game. Release engine after finishing game.
* ```elo```: The initial Elo rating.

Now you can start the match.

```
$python3 match_tool.py -e engine.json --num-games 100 --boardsize 19 --komi 7.5 --save-dir match
```

In addition, you may use the sample SGF directory ```19x19``` or generate the opening by [Sayuri](https://github.com/CGLemon/Sayuri) engine. Enter the GTP command ```genopenings <dir> <num games>```.
