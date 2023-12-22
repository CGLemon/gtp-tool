# gtp-tool

A pure python tool for GTP engine.

## Match

In recent years, the computer Go engine is significantly stronger than before. Two strong engines will prefer to play the same opening. The opening will affect the result. The main point is to use this tool instead of GoGui. It can sample the SGF from the provided set.

First we need a judge engine, such as GNU Go. We do not implement any rule for this tool. The judge engine helps us to judge the legal move and compute the final score. For Ubuntu user, you can download it via apt packet.

```
    sudo apt install gnugo
```

Then set up the configure for each engine. Fill the following data for each item.

* ```name```: The engine name.
* ```command```: command to run the engine.
* ```type```: One of ```player``` or ```judge```.

Now you can start the match.

```
    python3 match_tool.py -e engine.json -g 100
```

All options

* ```-e```: The engine configure.
* ```--sgf-dir```: Load the SGF file from here.
* ```--save-dir```: Save the SGF file here.
* ```--sample-rate```: The probability to start from SGF file.
* ```--boardsize```: Play the match games with this board size.
* ```--komi```: Play the match games with this komi.
* ```--num-games```: The number of played games.

You may use the sample SGF directory ```19x19``` or generate the opening by [Sayuri](https://github.com/CGLemon/Sayuri) engine. Enter the GTP command ```genopenings <dir> <num games>```.
