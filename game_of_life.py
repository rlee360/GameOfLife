#!/usr/bin/env python3
from multiprocessing import Process, Pool
from pathlib import Path
import pickle
import sys
import os
import numpy as np
import argparse
from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000
import matplotlib.pyplot as plt
from datetime import datetime
from scoop import futures

binary_formats = {"jpg", "jpeg", "png", "bmp", "tif"}
supported_formats = set([i for i in binary_formats] + ["txt"])

# Generating large random matrices tends to be very slow so we use this method
# https://stackoverflow.com/questions/34485591/memory-efficient-way-to-generate-a-large-numpy-array-containing-random-boolean-v
def fast_random_bool(shape):
    n = np.prod(shape)
    nb = -(-n // 8)     # ceiling division
    b = np.frombuffer(np.random.bytes(nb), np.uint8, nb)
    return np.unpackbits(b)[:n].reshape(shape).view(np.bool)

# Get middle factors of number
# Bad algorithm, but numbers are small
def factorize(num):
    factors = []
    for i in range(1,num+1):
        if num%i == 0:
            factors.append(i)
    if len(factors)%2 == 0: # nonsquare
        return (factors[len(factors)//2], factors[len(factors)//2 - 1])
    else: # square
        midpoint = (len(factors)-1)//2
        return (factors[midpoint], factors[midpoint])

def write_to_file(data, directory, fname, fmt):
    path = directory / f"{fname}.{fmt}"
    if fmt in binary_formats:
        Image.fromarray((255-data*255).astype(np.uint8)).save(path, quality=100)
    else:
        np.savetxt(path, data.view('uint8'), delimiter=' ', fmt='%d')

#run the game of life on an array padded
def life(arr):
    res = np.zeros(arr.shape, dtype='uint8')
    for row in range(1, int(arr.shape[0]-1)):
        for col in range(1, int(arr.shape[1]-1)):
            res[row, col] = arr[row-1, col-1] + arr[row-1, col] + arr[row-1, col+1] + \
                            arr[row, col-1] + arr[row, col+1] + \
                            arr[row+1, col-1] + arr[row+1, col] + arr[row+1, col+1]
    '''
    if cell is 1 and has between (1,4) neighbors lives
    if cell is 0 and has exactly 3 neighbors lives
    This array-wise logical comparison saves on checking multiple if
        statements (and thereby branches) for each cell
    '''
    return (((arr == 1) & (res > 1) & (res < 4)) | ((arr == 0) & (res == 3))).astype('uint8')

def unit_test_life():
    vertical = np.array([[0, 0, 0, 0, 0],
                         [0, 0, 1, 0, 0],
                         [0, 0, 1, 0, 0],
                         [0, 0, 1, 0, 0],
                         [0, 0, 0, 0, 0]])

    horizontal = np.array([[0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0],
                           [0, 1, 1, 1, 0],
                           [0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0]])

    assert np.array_equal(horizontal, life(vertical))
    assert np.array_equal(vertical, life(horizontal))

def get_padded_slice(cells_per_dim, block_size, offset):
    x = slice(offset * block_size, min(cells_per_dim + 2, (offset+1)*block_size + 2))
    return x

def get_unpadded_slice(cells_per_dim, block_size, offset):
    x = slice(offset * block_size + 1, min(cells_per_dim + 1, (offset + 1) * block_size + 1))
    return x

def main():
    parser = argparse.ArgumentParser(description='A Multi-threaded Python Application that Plays the Game of Life. '
                                                 'Must specify either random input data or input from file.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-e', '--evolutions', type=int, default=1,
                        help='Number of evolutions of game.')
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='Suggestion for number of threads to run the program on.')
    parser.add_argument('-i', '--input', type=str, default=None,
                            help='filename for input with either image data, binary data, or space separated text')
    parser.add_argument('-c', '--cutoff', type=int, default=128,
                        help='where to threshold image values if input is an image (higher the cutoff, the darker the initial image)')
    parser.add_argument('-r', '--random', type=str, default=None,
                        help='initialize a random start matrix. Format: ROWSxCOLUMNS')
    parser.add_argument('-p', '--plot', action='store_true', help='shows each evolution in a matplotlib window')
    parser.add_argument('-l', '--log', type=str, default=None,
                        help='if specified, saves each evolution of the input board to the specified directory')
    parser.add_argument('-f', '--format', type=str, default='bmp',
                        help=f'if specified, the program will save each evolution as this format. Only has effect if --log is also set. Independent of the actual output file format. Options={supported_formats}')
    parser.add_argument('-o', '--output', type=str, default='life_output.txt',
                        help='filename for output to either image data, or space separated text')
    parser.add_argument('-u', '--unit', action='store_true',
                        help='if specified, will run a unit test to ensure the life function is working properly. Program will exit afterward')

    # User has to specify some args
    args = parser.parse_args()

    if args.unit:
        print("Unit testing the life() function. Will raise AssertionError if unit test fails.")
        unit_test_life()
        sys.exit(0)

    # Can only specify input or random
    if (args.input is None and args.random is None) or (args.input is not None and args.random is not None):
        parser.print_help()
        print("\nERROR: need to specify either --input OR --random, not both", file=sys.stderr)
        sys.exit(1)
    elif args.input:
        if '.' in args.input and args.input.split('.')[1] in binary_formats:
            image_bytes = np.array(Image.open(args.input).convert('L'))
            input_bytes = (image_bytes < args.cutoff)
        else:
            with open(args.input, 'r') as f:
                input_bytes = np.loadtxt(f, delimiter=' ').astype('uint8')
    elif args.random:
        print('Generating input matrix...')
        input_bytes = fast_random_bool(tuple([int(el) for el in args.random.lower().split('x')][0:2]))
        print('Writing input matrix to file...')
        write_to_file(input_bytes, Path('./'), f"input_{datetime.now().strftime('%y-%m-%d-%H%M%S')}", args.format)

    if args.format not in supported_formats:
        parser.print_help()
        print(f"\nERROR: illegal format '{args.format}' specified, "
               f"please choose from {supported_formats}", file=sys.stderr)
        sys.exit(1)

    args.evolutions = max(1, int(args.evolutions))
    args.threads = max(1, int(args.threads)) # ensure no decimals
    (num_threads_r, num_threads_c) = factorize(args.threads)
    # we want more threads in the row direction if odd total because this is
    # more efficient in terms of memory caching
    num_rows = input_bytes.shape[0]
    num_cols = input_bytes.shape[1]
    block_size_r = int(np.ceil(num_rows/num_threads_r))
    block_size_c = int(np.ceil(num_cols/num_threads_c))

    padded = np.zeros((num_rows+2, num_cols+2), dtype='uint8')
    padded[1:-1, 1:-1] = input_bytes

    if args.plot:
        plt.figure(figsize=(24, 24))
        img = plt.imshow(padded[1:-1, 1:-1], cmap='Greys')
        plt.pause(0.001)
    
    # save the initial matrix to file.
    # for ease of scripting we 0 pad the numbers with the needed number of digits
    fname_padding = int(np.log10(args.evolutions))+1
    if args.log:
        write_to_file(padded[1:-1, 1:-1], Path(args.log), 
                      "{header}_evo_{evo:0{padding}d}_{curtime}"
                      .format(header=(args.input.split('.')[0] if args.input else args.random),
                              evo=0,
                              padding=fname_padding,
                              curtime=datetime.now().strftime('%y-%m-%d-%H%M%S'),
                              fmt=args.format),
                      args.format)

    '''
    for each evolution,
    split the padded matrix up into the number of parts
    append it to a list
    and use map to distribute this list to the pool of processes.
    
    we catch keyboard interrupts so the user can stop the plotting
    '''

    oldtime = datetime.now()

    print(f"Starting {num_threads_r * num_threads_c} threads")

    for evolution in range(1, args.evolutions + 1):
        try:
            if args.plot:
                img.set_data(padded[1:-1, 1:-1])
                plt.pause(0.0001)

            results = []
            for i in range(num_threads_r):
                for j in range(num_threads_c):
                    x = get_padded_slice(num_rows, block_size_r, i)
                    y = get_padded_slice(num_cols, block_size_c, j)
                    results.append(padded[x, y])

            newtime = datetime.now()
            if evolution == 1:
                print(f"Running Evolution {evolution}, Time elapsed N/A")
            else:
                print(f"Running Evolution {evolution}, Time elapsed {(newtime - oldtime)}")
            oldtime = newtime
            results = list(futures.map(life, results))

            counter = 0
            for i in range(num_threads_r):
                for j in range(num_threads_c):
                    padded[get_unpadded_slice(num_rows, block_size_r, i),
                           get_unpadded_slice(num_cols, block_size_c, j)] = results[counter][1:-1, 1:-1]
                    counter += 1

            if args.log:
                write_to_file(padded[1:-1, 1:-1], Path(args.log), 
                      "{header}_evo_{evo:0{padding}d}_{curtime}"
                      .format(header=(args.input.split('.')[0] if args.input else args.random),
                              evo=evolution,
                              padding=fname_padding,
                              curtime=datetime.now().strftime('%y-%m-%d-%H%M%S'),
                              fmt=args.format),
                      args.format)

        except KeyboardInterrupt:
            print("Interrupt received! Ending now.", file=sys.stderr)
            break


    final_result = padded[1:-1, 1:-1]
    # if the output filetype is an image type that we recognize it, 
    # save it as an image. Else as space separated text
    if '.' in args.output:
        out_split = args.output.split('.')
        write_to_file(final_result, Path('.'), out_split[-2], out_split[-1])
    else:
        write_to_file(final_result, Path('.'), args.output, args.format)

    # plot the start and stop states
    if not args.random and '.' in args.input and args.input.split('.')[1] in binary_formats:
        fig, (ax1, ax2, ax3) = plt.subplots(figsize=(24, 24), nrows=1, ncols=3)
        ax1.imshow(255 - image_bytes, cmap='Greys')
        ax2.imshow(input_bytes, cmap='Greys')
        ax3.imshow(final_result, cmap='Greys')
    else:
        fig, (ax1, ax2) = plt.subplots(figsize=(8.5,11), nrows=1, ncols=2)
        ax1.imshow(input_bytes, cmap='Greys')
        ax2.imshow(final_result, cmap='Greys')

    plt.show()

if __name__ == "__main__":
    main()
