import time
from packet import Packet, UnreliableChannel, verify_checksum

TIMEOUT = 2.0 # the countdown timer that is running when sender is waiting for ack (2 secs to wait before retransmitting)
MAX_RETRIES = 5 # retry sending pkt 5 times before stopping

class RDT30Sender:
    def __init__(self, channel):
        self.channel = channel
        self.seq_num = 0
        self.state = "WAIT_FOR_CALL"
        self.sent_count = 0
        self.retry_count = 0
    
    def send_pkt(self, data):
        # check if fsm is in waiting state
        if self.state != "WAIT_FOR_CALL":
            print(f"[SENDER] Error: Not ready to send. Still waiting for ACK!")
            return False
        
        pkt = Packet(seq_num = self.seq_num, data = data)
        retries = 0
        
        while retries < MAX_RETRIES:
            self.state = "WAIT_FOR_ACK"
            print(f"[SENDER] Sending: seq num: {self.seq_num}, data: '{self.data}'"
                  f"Attempt: {retries + 1}")
