# this is a utility file defining all the packet related funcs and classes

import random

# helper funcs
def calc_checksum(data):
    return sum(ord(c) for c in data)

def verify_checksum(packet):
    expected = calc_checksum(packet.data)
    return expected == packet.checksum


# packet class
class Packet:
    def __init__(self, seq_num, data="", is_ack=False, ack_num=1):
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack
        self.ack_num = ack_num
        self.checksum = calc_checksum(data)
    
    def __str__(self):
        if self.is_ack:
            return f"[ACK | ack num: {self.ack_num}]"
        else:
            return f"[PKT | seq: {self.seq_num}, data = {self.data}, checksum = {self.checksum}]"


# unreliable channel (cuz on the internet pkts can be lost, corrupted or delayed)
class UnreliableChannel:
    def __init__(self, loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2):
        self.loss_prob = loss_prob
        self.corrupt_prob = corrupt_prob
        self.delay_prob = delay_prob
    
    def transmit(self, packet, log_prefix=""):
        # 1 -- checking for loss
        if random.random() < self.loss_prob:
            print(f"{log_prefix} LOST PKT: {packet}")
            return None # the receiver gets nothing
        
        # 2 -- checking for corrupt pkt
        if random.random() < self.corrupt_prob:
            packet.checksum += 1 # different checksum
            print(f"{log_prefix} CORRUPTED PKT: {packet}")
            return packet
        
        # 3 -- checking for delay
        if random.random() < self.delay_prob:
            print(f"{log_prefix} DELAYED PKT: {packet}")

        print(f"{log_prefix} OK: {packet}")
        return packet
