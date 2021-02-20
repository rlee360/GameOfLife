import sys
import zmq
from paramiko import SSHClient, AutoAddPolicy
import pickle
from multiprocessing import Pool
from worker_serialize import *
import numpy as np

class WorkerSocket:
    def __init__(self, sock, host, port, num_threads, interpreter, abs_path):
        self.host = host
        self.port = int(port)
        self.num_threads = int(num_threads)
        self.sock = sock
        self.sock.connect(f"tcp://{self.host}:{self.port}")

    def __exit__(self):
        self.sock.send(EXIT_MSG)
        self.sock.close()

class Broker:
    def __init__(self, hosts):
        self.worker_socks = []
        self.local_threads = 0
        self.total_threads = 0
        self.client = SSHClient()
        self.client.load_system_host_keys()
        # self.client.set_missing_host_key_policy(AutoAddPolicy())
        self.context = zmq.Context()

        with open(hosts, 'r') as f:
            lines = []
            for line in f:
                if line.strip()[0] != '#':
                    lines.append([string for string in line.strip().split(' ') if len(string) > 0])
            for line in lines:
                host, num_threads, *others = line
                self.total_threads += int(num_threads)

                host, port = [it.lower() for it in host.split(':')]
                username, interpreter, abs_path, log_file, *args = others

                zmqsock = self.context.socket(zmq.REQ)
                worker_sock = WorkerSocket(zmqsock, host, port, num_threads, interpreter, abs_path)
                self.worker_socks.append(worker_sock)
                self.client.connect(host, username=username, password="")
                transport = self.client.get_transport()
                channel = transport.open_session()
                cmd = f"{interpreter} {abs_path} -p {port} -t {num_threads} {' '.join(args)} > {log_file} 2>&1"
                print(cmd)
                channel.exec_command(cmd)


        # del client, stdin, stdout, stderr
        if self.total_threads <= 0:
            raise Exception("Illegal Number of Threads Specified")

    def sock_gen(self, _data):
        cnt = 0
        for worker in self.worker_socks:
            yield (worker.sock, _data[cnt:cnt + worker.num_threads])
            cnt += worker.num_threads

    def send_off(self, payloads):
        if len(payloads) == 0:
            return
        cnt = 0
        for worker in self.worker_socks:
            payload = payloads[cnt:cnt+worker.num_threads]
            cnt += worker.num_threads
            dumped_bytes = dump_serial(payload)
            worker.sock.send(dumped_bytes, zmq.NOBLOCK)

    def receive(self):
        if len(self.worker_socks) == 0:
            return []
        results = []
        for worker in self.worker_socks:
            results.append(worker.sock.recv())
        true_results = []
        for sublist in results:
            sublist = load_serial(sublist)
            for datum in sublist:
                true_results.append(datum)
        return true_results

    def close(self):
        for worker in self.worker_socks:
            worker.__exit__()
        self.context.destroy()
        self.client.close()



    # def send_data(self, payload):
    #     safe_send(self.sock, SEND_REQUEST)
    #     data = receive_until(self.sock)
    #     if data == ACK_MSG:
    #         safe_send(self.sock, bytes(str(len(payload)), 'UTF-8') )
    #         self.sock.sendall(payload)
    #     data = receive_until(self.sock)
    #     if data == ACK_MSG:
    #         print("Data sent successfully")