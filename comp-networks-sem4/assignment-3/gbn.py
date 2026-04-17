import time
from packet import Packet, UnreliableChannel, verify_checksum

TIMEOUT = 2.0
MAX_RETRIES = 5


class GBNSender:
    def __init__(self, channel, win_size=4):
        self.channel = channel
        self.win_size = win_size
        self.base = 0
        self.next_seq = 0
        self.win = {}
        self.state = "READY"
        self.sent_count = 0
        self.retry_count = 0

        # seq space is twice the win size -- to avoid ambiguity
        self.seq_space = 2 * win_size

    def _win_available(self):
        in_flight = (self.next_seq - self.base) % self.seq_space
        return self.win_size - in_flight
    
    def send_all(self, data_list):
        total = len(data_list)
        next_data_i = 0
        retries = 0

        print(f"\n[GBN SENDER] starting.. win size: {self.win_size}"
              f"total ptks: {total}")
        
        while self.base < total and retries <= MAX_RETRIES:
            # 1 -- fill the window
            while(self._win_available() > 0 and next_data_i < total):
                self.state = "READY"

                seq = self.next_seq % self.seq_space
                data = data_list[next_data_i]
                pkt = Packet(seq_num=seq, data=data)

                print(f"\n[GBN SENDER] seq num: {seq}, sending: '{data}'"
                      f"[window: {self.base}..{self.base + self.win_size - 1}]")
                
                self.win[seq] = pkt
                self.channel.transmit(pkt, log_prefix="CHANNEL -> RX")

                self.next_seq += 1
                next_data_i += 1
            
            if self._win_available() == 0:
                self.state = "WINDOW_FULL"
                print(f"\n[GBN SENDER] window FULL"
                      f"(base: {self.base}, next: {self.next_seq})"
                      f"Waiting for ACKs...")
            
            
            # 2 -- simulate receiver processing in-flight pkts
            acks_this_round = []

            for i in range(self.base, next_data_i):
                seq = i % self.seq_space
                if seq not in self.win:
                    continue

                pkt = self.win[seq]

                ack = gbn_receiver_fsm(
                    self.channel.transmit(pkt, log_prefix=f"RETRY -> RX seq: {seq}"),
                    log_prefix=f"seq: {seq}"
                )

                if ack is not None:
                    ack_received = self.channel.transmit(ack, log_prefix="ACK->TX")
                    if ack_received is not None:
                        acks_this_round.append(ack_received)
            
            # 3 -- process received acks -> slide window
            for ack in acks_this_round:
                if not ack.is_ack or not verify_checksum(ack):
                    print(f"[GBN SENDER] Corrupted or invalid ACK - ignoring")
                    continue

                ack_n = ack.ack_num
                print(f"[GBN SENDER] ACK received for seq: {ack_n}")
                while self.base <= ack_n and self.base < total:
                    confirmed_seq = self.base % self.seq_space
                    if confirmed_seq in self.win:
                        print(f"[GBN SENDER] PKT seq: {confirmed_seq}"
                              f"(data idx {self.base}) acknowledged!!")
                        del self.win[confirmed_seq]
                        self.sent_count += 1
                    self.base += 1
                    retries = 0

            # 4 -- timeout check
            if self.base < next_data_i and len(acks_this_round) == 0:
                retries += 1
                self.retry_count += 1
                print(f"\n[GBN SENDER] TIMEOUT! No ACKs received..."
                      f"Going back to seq: {self.base % self.seq_space}"
                      f"retransmitting ALL {len(self.win)} window pkts..."
                      f"retry {retries}/{MAX_RETRIES}")
                
                self.next_seq = self.base
                next_data_i = self.base
                self.win.clear()
        if retries > MAX_RETRIES:
            print(f"\n[GBN SENDER] MAX retries exceeded!! STOPPING...")
        else:
            print(f"\n[GBN SENDER] ALL {self.sent_count} pkts ACKed")



_gbn_receiver_state = {
    "expected_seq": 0,
    "last_ack_num": -1,
    "received_data": []
}

def reset_gbn_receiver(seq_space=8):
    _gbn_receiver_state["expected_seq"] = 0
    _gbn_receiver_state["last_ack_num"] = -1
    _gbn_receiver_state["received_data"] = []

def gbn_receiver_fsm(packet, log_prefix=""):
    expected = _gbn_receiver_state["expected_seq"]

    # 1 -- PKT LOST
    if packet is None:
        print(f"[GBN RECEIVER {log_prefix}] PKT LOST! No ACK sent!")
        return None
    
    # 2 -- corrupted
    if not verify_checksum(packet):
        print(f"[GBN RECEIVER {log_prefix}] Corrupted! discarding..")
        if _gbn_receiver_state["last_ack_num"] >= 0:
            nak = Packet(seq_num=0, is_ack=True, ack_num=_gbn_receiver_state["last_ack_num"])
            return nak
        return None
    
    # 3 -- out of order pkt
    if packet.seq_num != expected:
        print(f"[GBN RECEIVER {log_prefix}] out of order!"
              f"got seq: {packet.seq_num}, expected: {expected}. discarding..")
        
        if _gbn_receiver_state["last_ack_num"] >= 0:
            dup_ack = Packet(seq_num=0, is_ack=True, ack_num=_gbn_receiver_state["last_ack_num"])
            return dup_ack
        return None
    
    # 4 -- correct pkt
    print(f"[GBN RECEIVER {log_prefix}] OK seq: {packet.seq_num}"
          f"data: '{packet.data}'")
    _gbn_receiver_state["received_data"].append(packet.data)
    _gbn_receiver_state["last_ack_num"] = packet.seq_num
    _gbn_receiver_state["expected_seq"] = (packet.seq_num + 1) 

    ack = Packet(seq_num=0, is_ack=True, ack_num=packet.seq_num)
    print(f"[GBN RECEIVER {log_prefix}] sendingg ACK({packet.seq_num})")
    return ack



# run simulations
def run_gbn(pkt_count=6, pkt_size=10, win_size=4, loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.1):
    print("=" * 65)
    print("GBN")
    print("=" * 65)
    print(f"Pkts to send: {pkt_count}")
    print(f"Window size: {win_size}")
    print(f"Packet Size: {pkt_size} chars")
    print(f"Loss probablity: {loss_prob}")
    print(f"Corrupt probablity: {corrupt_prob}")
    print(f"Delay probablity: {delay_prob}")
    print("=" * 65)

    reset_gbn_receiver(seq_space=2 * win_size)

    channel = UnreliableChannel(loss_prob, corrupt_prob, delay_prob)
    sender = GBNSender(channel, win_size=win_size)

    data_list = []
    for i in range(pkt_):
        data = f"PKT{i:02d}" + ("X" * max(0, pkt_size - 5))
        data_list.append(data[:pkt_size])

    sender.send_all(data_list)

    print("\n" + "=" * 65)
    print("Simulation Complete")
    print("=" * 65)
    print(f"Pkts ACKed: {sender.send_count}/{pkt_count}")
    print(f"Total retransmissions: {sender.retry_count}")
    print(f"Data Received (in order): ")
    for idx, d in enumerate(_gbn_receiver_state["received_data"]):
        print(f"    [{idx}] {d}")
    print("=" * 65)

