from multiprocessing import Pool
import pickle
import sys
import numpy as np
import argparse
from datetime import datetime
import zmq
from worker_serialize import *


binary_formats = {"jpg", "jpeg", "png", "bmp", "tif"}
supported_formats = set([i for i in binary_formats] + ["txt"])

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

def get_padded_slice(cells_per_dim, block_size, offset):
    x = slice(offset * block_size, min(cells_per_dim + 2, (offset+1)*block_size + 2))
    return x

def get_unpadded_slice(cells_per_dim, block_size, offset):
    x = slice(offset * block_size + 1, min(cells_per_dim + 1, (offset + 1) * block_size + 1))
    return x

def init_threads():
    parser = argparse.ArgumentParser(description='A Distributed Worker Script Python Application '
                                                 'that Plays the Game of Life. This script should '
                                                 'not be called manually.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='Number of threads to run the program on.')
    parser.add_argument('--timeout', type=str, default="01:00:00",
                        help='Timeout before program exits. Specified in HH:MM:SS format.')
    parser.add_argument('-p', '--port', type=int, default=3141,
                        help='Port that program listens on.')

    # User has to specify some args
    args = parser.parse_args()

    timeouts = [int(i) for i in args.timeout.split(':')]
    if len(timeouts) != 3:
        parser.print_help()
        print(f"\nERROR: Timeout {args.timeout} should be in HH:MM:SS format.", file=sys.stderr)
        sys.exit(1)

    timeout_in_ms = 1000*(timeouts[0] * 3600 + timeouts[1] * 60 + timeouts[2])

    return max(1, int(args.threads)), int(args.port), timeout_in_ms

def work(num_threads, port, timeout_in_ms):
    pool = Pool(num_threads)
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    poller = zmq.Poller()
    poller.register(socket, flags=zmq.POLLIN)
    print('Ready to Work!', flush=True)

    while True:
        try:
            if poller.poll(timeout=timeout_in_ms):
                data = socket.recv()
            else:
                print('Timeout hit, exiting')
                break

            if data == EXIT_MSG:
                print('Exit message received! Exiting.', flush=True)
                break
            else:
                data = load_serial(data)

            oldtime = datetime.now()
            results = pool.map(life, data)
            newtime = datetime.now()
            print(f"Running data. Time elapsed: {(newtime - oldtime)}", flush=True)
            socket.send(dump_serial(results))
        # except zmq.Again as e:
        #     continue
        except KeyboardInterrupt:
            print("Received a keyboard interrupt. Exiting.", flush=True)
            break

    poller.unregister(socket)
    pool.close()
    socket.close()

work(*init_threads())