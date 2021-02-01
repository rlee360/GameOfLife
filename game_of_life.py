from multiprocessing import Process, Manager, Pool
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

# Generating large random matrices tends to be very slow so we use this method
# https://stackoverflow.com/questions/34485591/memory-efficient-way-to-generate-a-large-numpy-array-containing-random-boolean-v
def fast_random_bool(shape):
    n = np.prod(shape)
    nb = -(-n // 8)     # ceiling division
    b = np.frombuffer(np.random.bytes(nb), np.uint8, nb)
    return np.unpackbits(b)[:n].reshape(shape).view(np.bool)

def write_to_file(data, path):
    np.savetxt(path, data*1, delimiter=' ', fmt='%d')

#run the game of life on an array padded
def life(arr):
    res = np.zeros(arr.shape)
    for row in range(1, int(arr.shape[0]-1)):
        for col in range(1, int(arr.shape[1]-1)):
            num_alive = 0
            for rdir in range(-1,2):
                for cdir in range(-1,2):
                    if rdir == 0 and cdir == 0:
                        continue
                    if row+rdir < 0 or row+rdir >= arr.shape[0]:
                        continue
                    if col+cdir < 0 or col+cdir >= arr.shape[1]:
                        continue
                    num_alive += arr[row+rdir, col+cdir]
            if arr[row, col] == 1:
                if num_alive <= 1:
                    res[row, col] = 0
                elif num_alive == 2 or num_alive == 3:
                    res[row, col] = 1
                elif num_alive >= 4:
                    res[row, col] = 0
            elif arr[row,col] == 0:
                if num_alive == 3:
                    res[row, col] = 1
                else:
                    res[row, col] = 0
    return res

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

def main():
    binary_formats = {"jpg", "jpeg", "png", "bmp"}

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
                        help='Threshold if input is an image.')
    parser.add_argument('-r', '--random', type=str, default=None,
                        help='initialize a random start matrix. Format: ROWSxCOLUMNS')
    parser.add_argument('-p', '--plot', action='store_true', help='shows each evolution in a matplotlib window')
    parser.add_argument('-l', '--log', type=str, default=None,
                        help='if specified, saves each evolution of the input board to the specified directory as a space separated text file')
    parser.add_argument('-o', '--output', type=str, default='life_output.txt',
                        help='filename for output to either image data, or space separated text')
    parser.add_argument('-u', '--unit', action='store_true',
                        help='if specified, will run a unit test to ensure the life function is working properly. Program will exit afterward')

    # User has to specify some args
    args = parser.parse_args()

    if args.unit:
        print("Unit testing the life() function. Will result in AssertionError if unit test fails.")
        unit_test_life()
        sys.exit(0)

    # Can only specify input or random
    if (args.input is None and args.random is None) or (args.input is not None and args.random is not None):
        parser.print_help()
        print("\nError: need to specify either --input OR --random, not both", file=sys.stderr)
        sys.exit(1)
    elif args.input:
        if '.' in args.input and args.input.split('.')[1] in binary_formats:
            image_bytes = np.array(Image.open(args.input).convert('L'))
            input_bytes = image_bytes < args.cutoff
        else:
            data_load = []
            with open(args.input, 'r') as f:
                for line in f:
                    data_load.append([True if int(el) != 0 else False for el in line.strip().split(' ')])
            input_bytes = np.array(data_load)
    elif args.random:
        input_bytes = fast_random_bool(tuple([int(el) for el in args.random.lower().split('x')][0:2]))
        write_to_file(input_bytes, Path('./') / f"input_{datetime.now().strftime('%y-%m-%d-%H%M%S')}.txt")

    num_threads = np.ceil(np.sqrt(max(1, args.threads))) #ensure at least 1 thread if user specifies 0
    num_rows = input_bytes.shape[0]
    num_cols = input_bytes.shape[1]
    block_size_r = int(np.ceil(num_rows/num_threads))
    block_size_c = int(np.ceil(num_cols/num_threads))
    final_result = np.zeros(input_bytes.shape)
    final_result[::,::] = input_bytes

    padded = np.zeros((num_rows+2, num_cols+2), dtype='int')

    def get_padded_slice(cells_per_dim, block_size, offset):
        x = slice( max(0, offset * (block_size)), min(cells_per_dim + 2, offset * block_size + block_size + 2) )
        return x

    def get_unpadded_slice(index, offset):
        return slice(index * offset, (index + 1) * offset)

    if args.plot:
        plt.figure(figsize=(24, 24))
        img = plt.imshow(final_result, cmap='Greys')
        plt.pause(0.001)

    oldtime = datetime.now()

    results = []
    for i in range(int(np.ceil(num_rows / block_size_r))):
        for j in range(int(np.ceil(num_cols / block_size_c))):
            x = get_padded_slice(num_rows, block_size_r, i)
            y = get_padded_slice(num_cols, block_size_c, j)
            results.append(padded[x, y])

    print(f"Starting {len(results)} threads", file=sys.stderr)
    pool = Pool(len(results))
    
    # save the initial matrix to file.
    # for ease of scripting, we 0 pad the numbers
    fname_padding = int(np.log10(args.evolutions))+1
    if args.log:
        write_to_file(final_result, Path(args.log) / 
                      "{header}_evo_{evo:0{padding}d}_{curtime}.txt"
                      .format(header=(args.input.split('.')[0] if args.input else args.random),
                              evo=0,
                              padding=fname_padding,
                              curtime=datetime.now().strftime('%y-%m-%d-%H%M%S')))

    '''
    for each evolution,
    split the padded matrix up into the number of parts
    append it to a list
    and use map to distribute this list to the pool of processes.
    
    we catch keyboard interrupts so the user can cut the program at anytime
    and view the result.
    '''
    for evolution in range(1, args.evolutions + 1):
        try:
            if args.plot:
                img.set_data(final_result)
                plt.pause(0.0001)

            padded[1:num_rows+1, 1:num_cols+1] = final_result
            results = []
            for i in range(int(np.ceil(num_rows / block_size_r))):
                for j in range(int(np.ceil(num_cols / block_size_c))):
                    x = get_padded_slice(num_rows, block_size_r, i)
                    y = get_padded_slice(num_cols, block_size_c, j)
                    results.append(padded[x, y])

            newtime = datetime.now()
            if evolution == 1:
                print(f"Running Evolution {evolution}, Time elapsed N/A")
            else:
                print(f"Running Evolution {evolution}, Time elapsed {(newtime - oldtime)}")
            oldtime = newtime
            results = pool.map(life, results)

            counter = 0
            for i in range(int(np.ceil(num_rows / block_size_r))):
                for j in range(int(np.ceil(num_cols / block_size_c))):
                    final_result[get_unpadded_slice(i, block_size_r), get_unpadded_slice(j, block_size_c)] = results[counter][1:-1, 1:-1]
                    counter += 1

            if args.log:
                write_to_file(final_result, Path(args.log) / 
                              "{header}_evo_{evo:0{padding}d}_{curtime}.txt"
                              .format(header=(args.input.split('.')[0] if args.input else args.random),
                                      evo=evolution,
                                      padding=fname_padding,
                                      curtime=datetime.now().strftime('%y-%m-%d-%H%M%S')))

        except KeyboardInterrupt:
            print("Interrupt received! Ending now.", file=sys.stderr)
            break

    pool.close()

    # if the output filetype is an image type that we recognize it, save it as an image. Else as space separated text
    if '.' in args.output and args.output.split('.')[1] in binary_formats:
        Image.fromarray((255-final_result*255).astype(np.uint8)).save(args.output, quality=100)
    else:
        write_to_file(final_result, Path('.') / args.output)

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


main()