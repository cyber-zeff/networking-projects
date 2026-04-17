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
            
            # send pkt through the unreliable channel
            received_at_receiver = self.channel.transmit(pkt, log_prefix="CHANNEL -> RX")

            ack = rdt30_receiver_fsm(received_at_receiver, self.seq_num)
            
            # timer started
            start_time = time.time()

            if ack is not None:
                ack_received = self.channel.transmit(ack, log_prefix="CHANNEL -> TX")
            else:
                ack_received = None

            elapsed = time.time() - start_time


            # FSM Decides if we got a valid ACK or not
            if self._is_valid_ack(ack_received):
                print(f"[SENDER] seq num: {self.seq_num}, ACK received!"
                      f"Packet delivered successfully")
                self.seq_num = 1 - self.seq_num # flipping 0 -> 1 and vice versa
                self.state = "WAIT_FOR_CALL"
                self.send_count += 1
                return True
            
            else:
                retries += 1
                self.retry_count += 1
                reason = "timeout/lost" if ack_received is None else "corrupted ACK"
                print(f"[SENDER] seq num: {self.seq_num}, {reason.upper()}"
                      f"retransmitting... (retry: {retries}/{MAX_RETRIES})")
            
        print(f"[SENDER] seq num: {self.seq_num}, MAX RETRIES REACHED")
        self.state = "WAIT_FOR_CALL"
        return False
    

    # helper func -> checks if an ACK is valid or not
    def _is_valid_ack(self, ack):
        if ack is None:
            return False
        if not ack.is_ack:
            return False
        if not verify_checksum(ack):
            return False
        if ack.ack_num != self.seq_num:
            return False
        
        return True



_receiver_state = {
    "expected_seq": 0,
    "last_ack_sent": -1,
    "received_data": []
}

def reset_receiver():
    _receiver_state["expected_seq"] = 0
    _receiver_state["last_ack_sent"] = -1
    _receiver_state["received_data"] = []