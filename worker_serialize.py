import pickle

EXIT_MSG = b'Time to Exit!'

def dump_serial(_data):
    return pickle.dumps(_data, protocol=4)


def load_serial(_data):
    return pickle.loads(_data)
