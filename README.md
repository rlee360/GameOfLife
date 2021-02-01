# ECE465 HW1 - game_of_life.py 1.0


## Overview
We developed a program to run Conway's Game of Life in a multicore fashion. It can use images, space separated files of zeros and ones to seed the initial state, or seed a random initial state. The program takes an input matrix, slices it into sections, and performs the same Game of Life operations, in parallel, across a user-specifiable number of CPU cores. The algorithm runs in O(n x m x r) where n and m are the dimensions of the initial state, and r is the number of evolutions. We demonstrated this by timing progressively larger, randomly initialized matrices over 10 evolutions, running on 16 threads:

| Dimensions   | Average Time | Factor of Increase from Previous |
|--------------|--------------|----------------------------------|
| 100x100      | 0.01897      | N/A                              |
| 1000x100     | 0.09212      | 4.856                            |
| 1000x1000    | 0.87536      | 9.502                            |
| 10000x1000   | 8.78831      | 10.040                           |
| 10000x10000  | 88.87512     | 10.113                           |
| 100000x10000 | 896.23381    | 10.084                           |

We note an increase of only ~5 times from 100x100 to 1000x100, when we would expect there to be an increase of 10 times. We attribute this to there being a minimum time needed to copy the necessary data to each thread and perform the task switch, causing the smaller 100x100 case to take longer than just the time it took to perform the Game of Life operations. However, for very large data, we note that we get a slightly larger than 10 times increase, which we posit could be due to the overhead of slicing large arrays.

To demonstrate that running across multiple cores provides an appreciable performance boost, we run a randomly initialized 1000x1000 matrix on a single core and multiple cores:

| Number of Threads | Average Time | Speed Up Factor |
|-------------------|--------------|-----------------|
| 1                 | 9.2289       | N/A             |
| 4                 | 2.2408       | 4.119           |
| 16                | 0.8754       | 2.560           |

However, we do note diminishing returns as the number of cores increases, which we again attribute to the overhead of slicing the original matrix for each core to process each evolution.

## Results

The program allows a `-u` option that will perform a unit test with a very basic 1x3 block, which will rotate 90 degrees each evolution.

For a more complex example, we tested the gosper glider gun, which was the, "first known finite pattern with unbounded growth" and was found by Bill Gosper in November 1970" (See second acknowledgement).

![](gosper.gif)

As an additional example, we tested a 400x400 pixel 'X', which creates various patterns over many evolutions:

![](x.gif)

Finally, we tested an image over 600 evolutions (thresholded image is shown for 1 second and first evolution is shown for 1 second):

<img src="professor.gif" width="250"/>

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

Alternatively, a user can install the packages system wide, which can be performed using


## Usage
You must specify either random input data _or_ input from file. Arguments:

```
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
                        Threshold if input is an image. (default: 128)
  -r RANDOM, --random RANDOM
                        initialize a random start matrix. Format:
                        ROWSxCOLUMNSxCHANNELS (default: None)
  -p, --plot            shows each evolution in a matplotlib window (default:
                        False)
  -l LOG, --log LOG     saves each evolution of the input board to the
                        specified directory as a .npy file (default: None)
  -o OUTPUT, --output OUTPUT
                        filename for output to either image data, binary data,
                        or space separated text (default: life_output.txt)
```

## License
All rights reserved.

## Acknowledgements
https://stackoverflow.com/questions/34485591/memory-efficient-way-to-generate-a-large-numpy-array-containing-random-boolean-v
for fast random boolean generation

https://www.conwaylife.com/wiki/Gosper_glider_gun for an explanation of the Gosper Glider Gun
