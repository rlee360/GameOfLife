# ECE465 HW1 Conway's Game Of Life Implementation

## Conway's Game of Life
Conway's Game of Life is a zero player cellular automaton created by John Conway. The universe is a two dimensional grid of cells that are either alive or dead and interact with each of their 8 neighbors. At each time step (evolution), the following rules apply:

1. A live cell with less than two neighbors dies, as if by underpopulation
2. A live cell with two to three neighbors lives
3. A live cell with more than three neighbors dies, as if by over population
4. A dead cell with exactly three neighbors becomes live as if by reproduction.

Following these rules, an initial configuration can evolve to create various patterns. The game is Turing complete, and can simulate any other Turing Machine.

## Overview
We developed a program to run Conway's Game of Life in a multicore fashion. It can use images, space separated files of zeros and ones to seed the initial state, or seed a random initial state. The program takes an input matrix, slices it into sections, and performs the same Game of Life operations, in parallel, across a user-specifiable number of CPU cores. The algorithm runs in O(n x m x r) where n and m are the dimensions of the initial state, and r is the number of evolutions. We demonstrated this by timing progressively larger, randomly initialized matrices over 10 evolutions, running on 16 threads:

| Dimensions   | Average Time (sec) | Factor of Increase from Previous |
|--------------|--------------------|----------------------------------|
| 100x100      | 0.00512            | N/A                              |
| 1000x100     | 0.03810            | 7.441                            |
| 1000x1000    | 0.26718            | 7.012                            |
| 10000x1000   | 2.62055            | 9.808                            |
| 10000x10000  | 26.43361           | 10.087                           |
| 100000x10000 | 265.06325          | 10.028                           |

We note an increase of only ~7 times from 100x100 to 1000x100, when we would expect there to be an increase of 10 times. We attribute this to there being a minimum time needed to copy the necessary data to each thread and perform the task switch, and percentage-wise, this time affects the smaller 100x100 case more than the 1000x100 case. However, for very large data, we note that we get a roughly 10 times performance increase.

To demonstrate that running across multiple cores provides near theoretical performance boost, we run an 8k (7680x4320) image on a single core and multiple cores for 10 evolutions:

| Number of Threads | Average Time (sec) | Speed Up Factor |
|-------------------|--------------------|-----------------|
| 1                 | 88.7881            | N/A             |
| 2                 | 43.8825            | 2.023           |
| 4                 | 21.5458            | 2.037           |
| 8                 | 11.9831            | 1.798           |
| 16                |  8.8253            | 1.3578          |

However, we do note diminishing returns as the number of cores increases, which we again attribute to the overhead of slicing the original matrix for each core to process each evolution, and then copying the data back to re-create the new matrix.

## Results

The program allows a `-u` option that will perform a unit test with a very basic 1x3 block, which will rotate 90 degrees each evolution.

For a more complex example, we tested the gosper glider gun, which was the, "first known finite pattern with unbounded growth and was found by Bill Gosper in November 1970" (See second acknowledgement).

<img src="gosper.gif" width="500"/>

As an additional example, we tested a 400x400 pixel 'X', which creates various patterns over many evolutions:

<img src="x.gif" width="500"/>

Finally, we tested an image over 600 evolutions (thresholded image is shown for 1 second and first evolution is shown for 1 second):

<img src="professor.gif" width="500"/>

## Installation

After cloning this project, the user can make a choice to use a virtual environment. It is often recommended to run python scripts using a virtual environment (venv) to minimize package version conflicts. It can be installed on most Ubuntu/Debian based systems with the command `sudo apt install python3-venv`.

To create the venv and activate it:

```bash
python3 -m venv env  #creates the environment
source env/bin/activate  #activates the virtual environment
```

To install the required packages, use pip:
```bash
pip install -r requirements.txt
```

Alternatively, a user can install the packages system-wide, which can be performed using the system-wide pip or the distribution's package manager. Users pursuing this option are advised to read the requirements file and locate corresponding packages in their system repositories.

The next step is to set up SSH connections to all nodes. There is no other way to run the program; the simplest case would be running one node which is the same machine as the one running the program. The instructions must still be followed. To begin, install a standards-compliant SSH server and enable it. On every machine, create a user with the same name as the user that will be running the program. Set up passwordless authentication on the SSH servers for those users as documented (OpenSSH users might find the `ssh-copy-id` helper script useful). Create a hostfile with the following format:

```
HOST1 NUM_THREADS_1
HOST2 NUM_THREADS_2
...
```

for all hosts. Finally, ensure that the full path of the working directory of the machine running the program is mirrored on every node.

## Usage
You must specify either random input data _or_ input from file. Arguments:

```
usage: launcher.sh HOSTFILE_PATH [-h] [-e EVOLUTIONS] [-t THREADS] [-i INPUT]
                       [-c CUTOFF] [-r RANDOM] [-p] [-l LOG] [-f FORMAT]
                       [-o OUTPUT] [-u]

A Multi-threaded Python Application that Plays the Game of Life. Must specify
either random input data or input from file.

optional arguments:
  -h, --help            show this help message and exit
  -e EVOLUTIONS, --evolutions EVOLUTIONS
                        Number of evolutions of game. (default: 1)
  -t THREADS, --threads THREADS
                        Suggestion for number of threads to run the program
                        on. (default: 4)
  -i INPUT, --input INPUT
                        filename for input with either image data, binary
                        data, or space separated text (default: None)
  -c CUTOFF, --cutoff CUTOFF
                        where to threshold image values if input is an image
                        (higher the cutoff, the darker the initial image)
                        (default: 128)
  -r RANDOM, --random RANDOM
                        initialize a random start matrix. Format: ROWSxCOLUMNS
                        (default: None)
  -p, --plot            shows each evolution in a matplotlib window (default:
                        False)
  -l LOG, --log LOG     if specified, saves each evolution of the input board
                        to the specified directory (default: None)
  -f FORMAT, --format FORMAT
                        if specified, the program will save each evolution as
                        this format. Only has effect if --log is also set.
                        Independent of the actual output file format.
                        Options={'bmp', 'jpg', 'jpeg', 'png', 'txt', 'tif'}
                        (default: bmp)
  -o OUTPUT, --output OUTPUT
                        filename for output to either image data, or space
                        separated text (default: life_output.txt)
  -u, --unit            if specified, will run a unit test to ensure the life
                        function is working properly. Program will exit
                        afterward (default: False)
```

Example to run 1000x1000 random data on 4 threads for 20 evolutions, plotting each evolution and saving the output to a space separated text file:

```bash
./launcher.sh hostfile --random 1000x1000 --threads 4 --output 1000x1000.txt --evolutions 20 --plot
```

Example to run the gosper glider gun on 4 threads for 100 evolutions, plotting each evolution and saving each evolution to text file in a directory called gosper, finally saving the output to a space separated text file:

```bash
./launcher.sh hostfile --input gosper_glider.txt --threads 4 \
                       --output gosper.txt --evolutions 100 --plot --log ./gosper/ --format txt
```

Example to run the 'X' on 4 threads for 1000 evolutions, without plotting any data, except for the final result, and saving the final result to a bitmap:

```bash
./launcher.sh hostfile -i cross_center.txt -t 4 -o x.bmp -e 1000
```

Example to run the professor.jpg on 16 threads for 600 evolutions, without plotting any data, except for the final result, but logging each evolution to a bitmap, and the final result to a bmp.

```bash
./launcher.sh hostfile -i professor.jpg -t 16 -o professor.bmp -e 600 -l professor/ -f bmp
```

## License
All rights reserved.

## Acknowledgements
https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life for a detailed explanation of the history and premise of the game of life.
https://stackoverflow.com/questions/34485591/memory-efficient-way-to-generate-a-large-numpy-array-containing-random-boolean-v
for fast random boolean generation

https://www.conwaylife.com/wiki/Gosper_glider_gun for an explanation of the Gosper Glider Gun
