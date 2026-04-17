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
                    print(f"[GBN SENDER] Corrupted or invalid ACK")