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
        
        while retries <= MAX_RETRIES:
            self.state = "WAIT_FOR_ACK"
            print(f"[SENDER] Sending: seq num: {self.seq_num}, data: '{data}'"
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
                self.sent_count += 1
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

def rdt30_receiver_fsm(packet, exp_seq):
    # can be multiple cases here
    # case 1 -- pkt is lost while in transit
    if packet is None:
        print(f"[RECEIVER] PKT LOST. No ACK sent.")
        return None
    
    # case 2 -- pkt is corrupted
    if not verify_checksum(packet):
        print(f"[RECEIVER] PKT Corrupted. Send ACK for prev seq (DUP ACK = NAK)")
        prev_seq = 1 - exp_seq
        nak = Packet(seq_num=0, data="", is_ack=True, ack_num=prev_seq)
        return nak
    
    # case 3 -- pkt has wrong seq num
    if packet.seq_num != exp_seq:
        print(f"[RECEIVER] DUP! Got seq={packet.seq_num}"
              f"expected seq is: {exp_seq}. Re-sending old ACK.")
        
        prev_seq = 1 - exp_seq
        dup_ack = Packet(seq_num=0, data="", is_ack=True, ack_num=packet.seq_num)
        return dup_ack
    
    # case 4 -- no issues
    print(f"[RECEIVER] Received correctly: seq_num: {packet.seq_num}"
          f"data: '{packet.data}'")
    _receiver_state["received_data"].append(packet.data)
    _receiver_state["last_ack_sent"] = packet.seq_num

    # send ack for this seq num
    ack = Packet(seq_num=0, data="", is_ack=True, ack_num=packet.seq_num)
    print(f"[RECEIVER] Sending ACK for seq: {packet.seq_num}")
    return ack


# sample run simulation
def run_rdt30(pkt_count=5, pkt_size=10, loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2, timeout=TIMEOUT):
    print("=" * 65)
    print("rdt 3.0 -- Stop-and-Wait Protocol")
    print("=" * 65)
    print(f"Pkts to send: {pkt_count}")
    print(f"pkt size: {pkt_size}")
    print(f"Loss probablity: {loss_prob}")
    print(f"Corrupt probablity: {corrupt_prob}")
    print(f"Delay probablity: {delay_prob}")
    print(f"Timeout: {timeout}s")
    print("=" * 65)


    reset_receiver()
    channel = UnreliableChannel(loss_prob, corrupt_prob, delay_prob)
    sender = RDT30Sender(channel)

    for i in range(pkt_count):
        data = f"PKT{i:02d}" + ("X" * max(0, pkt_size - 5))
        data = data[:pkt_size]
        sender.send_pkt(data)

    print("\n" + "=" * 65)
    print("Simulation Complete")
    print("=" * 65)
    print(f"Pkts sent successfully: {sender.sent_count}/{pkt_count}")
    print(f"Total retransmissions: {sender.retry_count}")
    print(f"Data Received (in order): ")
    for idx, d in enumerate(_receiver_state["received_data"]):
        print(f"    [{idx}] {d}")
    print("=" * 65)


if __name__ == "__main__":
    print("\n>>> SCENARIO 1 -- Clean run (no loss, no corruption)")
    run_rdt30(pkt_count=4, pkt_size=10, loss_prob=0.0, corrupt_prob=0.0, delay_prob=0.0)

    print("\n>>> SCENARIO 2 -- PKT LOSS only")
    run_rdt30(pkt_count=4, pkt_size=10, loss_prob=0.5, corrupt_prob=0.0, delay_prob=0.0)

    print("\n>>> SCENARIO 3 -- Corruption only")
    run_rdt30(pkt_count=4, pkt_size=10, loss_prob=0.0, corrupt_prob=0.5, delay_prob=0.0)

    print("\n>>> SCENARIO 4 -- all (loss + corruption + delay)")
    run_rdt30(pkt_count=4, pkt_size=10, loss_prob=0.3, corrupt_prob=0.3, delay_prob=0.2)