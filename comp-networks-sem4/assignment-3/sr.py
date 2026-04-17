import time
from packet import Packet, UnreliableChannel, verify_checksum

TIMEOUT = 2.0
MAX_RETRIES = 5

class SRSender:
    def __init__(self, channel, win_size=4):
        self.channel = channel
        self.win_size = win_size
        self.seq_space = 2 * win_size
        self.base = 0
        self.next_seq = 0
        self.win = {}
        self.acked = {}
        self.retrasmit = {}
        self.sent_count = 0
        self.retry_count = 0
        self.state = "READY"
    
    def _win_available(self):
        in_flight = (self.next_seq - self.base) % self.seq_space
        return self.win_size - in_flight
    
    def send_all(self, data_list):
        total       = len(data_list)
        next_data_i = 0
        retries     = 0

        print(f"\n[SR SENDER] starting.. window size: {self.win_size}"
              f"total pkts: {total}")
        
        while self.base < total and retries <= MAX_RETRIES:
            # 1 -- fill the win with new pkts
            while self._win_available() > 0 and next_data_i < total:
                self.state = "READY"
                seq = self.next_seq % self.seq_space
                data = data_list[next_data_i]
                pkt = Packet(seq_num=seq, data=data)

                print(f"\n[SR SENDER] seq: {seq}, sending: '{data}'"
                      f"[window: {self.base % self.seq_space}..."
                      f"{(self.base + self.win_size - 1) % self.seq_space}]")
                
                self.win[seq] = pkt
                self.acked[seq] = False
                self.retransmit[seq] = False

                self.channel.transmit(pkt, log_prefix="CHANNEL -> RX")
                self.next_seq += 1
                next_data_i += 1

            
            if self._win_available() == 0:
                self.state = "WINDOW_FULL"
                print(f"\n[SR SENDER] window is FULL. waiting for ACKs...")
            

            # 2 -- simulate receiver processing each in-flight pkt
            acks_received = []
 
            for i in range(self.base, next_data_i):
                seq = i % self.seq_space
 
                if seq not in self.window:
                    continue
 
                pkt = self.window[seq]
 
                arrived = self.channel.transmit(
                    pkt, log_prefix=f"DELIVER -> RX seq={seq}"
                )

                ack = sr_receiver_fsm(arrived, log_prefix=f"seq={seq}")
 
                if ack is not None:
                    ack_back = self.channel.transmit(
                        ack, log_prefix=f"ACK -> TX seq={ack.ack_num}"
                    )
                    if ack_back is not None:
                        acks_received.append(ack_back)

            # 3 -- process individual ACKs
            got_new_ack = False
 
            for ack in acks_received:
                if not ack.is_ack or not verify_checksum(ack):
                    print(f"[SR SENDER] Corrupted ACK — ignoring.")
                    continue
 
                ack_n = ack.ack_num
                print(f"[SR SENDER] ACK received for seq={ack_n}")
 
                if ack_n in self.acked:
                    self.acked[ack_n] = True
                    self.retransmit[ack_n] = False
                    got_new_ack = True
                    print(f"[SR SENDER] Marked seq={ack_n} as ACKed.")

            # 4 -- move window forward
            while self.base < total:
                base_seq = self.base % self.seq_space
                if base_seq in self.acked and self.acked[base_seq]:
                    print(f"[SR SENDER] sliding window: base {self.base}"
                          f"{self.base + 1} (seq={base_seq} confirmed)")
                    del self.win[base_seq]
                    del self.acked[base_seq]
                    self.sent_count += 1
                    self.base += 1
                    retries = 0
                else:
                    break # cannot slide more b/c base not yet ACKed

            # 5 -- timeout
            if not got_new_ack and self.base < next_data_i:
                retries          += 1
                self.retry_count += 1
 
                print(f"\n[SR SENDER] TIMEOUT (retry {retries}/{MAX_RETRIES}). "
                      f"Selectively retransmitting unACKed pkts...")
 
                for i in range(self.base, next_data_i):
                    seq = i % self.seq_space
                    if seq in self.acked and not self.acked[seq]:
                        print(f"[SR SENDER] Retransmitting seq={seq} only.")
                        self.channel.transmit(
                            self.window[seq],
                            log_prefix=f"RETX -> RX seq={seq}"
                        )
 
        if retries > MAX_RETRIES:
            print(f"\n[SR SENDER] Max retries exceeded.")
        else:
            print(f"\n[SR SENDER] All {self.sent_count} pkts acknowledged!")



_sr_receiver_state = {
    "rcv_base"     : 0,
    "buffer"       : {},
    "received_data": [],
    "window_size"  : 4,
}
 
def reset_sr_receiver(window_size=4):
    _sr_receiver_state["rcv_base"] = 0
    _sr_receiver_state["buffer"] = {}
    _sr_receiver_state["received_data"] = []
    _sr_receiver_state["window_size"] = window_size
 
 
def sr_receiver_fsm(packet, log_prefix=""):
    rcv_base = _sr_receiver_state["rcv_base"]
    window_size = _sr_receiver_state["window_size"]
    seq_space = 2 * window_size
    buf = _sr_receiver_state["buffer"]
 
    # case 1 -- lost
    if packet is None:
        print(f"[SR RECEIVER {log_prefix}] PKT lost. No ACK.")
        return None
 
    # case 2 -- corrupted
    if not verify_checksum(packet):
        print(f"  [SR RECEIVER {log_prefix}] Corrupted! Discarding.")
        return None
 
    seq = packet.seq_num
 
    # case 3 -- pkt is correct
    if seq == rcv_base % seq_space:
        print(f"  [SR RECEIVER {log_prefix}] ✅ In-order seq={seq} "
              f"data='{packet.data}'. Buffering and delivering.")
 
        buf[seq] = packet.data
 
        while (_sr_receiver_state["rcv_base"] % seq_space) in buf:
            s = _sr_receiver_state["rcv_base"] % seq_space
            _sr_receiver_state["received_data"].append(buf[s])
            print(f"  [SR RECEIVER] Delivered seq={s} → '{buf[s]}'")
            del buf[s]
            _sr_receiver_state["rcv_base"] += 1
 
        ack = Packet(seq_num=0, is_ack=True, ack_num=seq)
        print(f"  [SR RECEIVER] Sending ACK({seq})")
        return ack
    
    # case 4 -- pkt is out of order but is within the receive window
    offset = (seq - rcv_base % seq_space) % seq_space
    if offset < window_size:
        print(f"[SR RECEIVER {log_prefix}] Out-of-order seq={seq} "
              f"(expected={rcv_base % seq_space}). "
              f"BUFFERING (not discarding like GBN!).")
 
        buf[seq] = packet.data
 
        ack = Packet(seq_num=0, is_ack=True, ack_num=seq)
        print(f"  [SR RECEIVER] Sending ACK({seq}) for buffered pkt.")
        return ack
 
    # case 5 -- outside receive window -> discard
    print(f"[SR RECEIVER {log_prefix}] seq={seq} outside window. Discarding..")
    return None
 

def run_sr(pkt_count=6, pkt_size=10, win_size=4,
           loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.1):

    print("=" * 65)
    print("SR Protocol Simulation")
    print("=" * 65)
    print(f"Pkts to send: {pkt_count}")
    print(f"Window size (N): {win_size}")
    print(f"pkt size: {pkt_size} chars")
    print(f"Loss prob: {loss_prob}")
    print(f"Corrupt prob: {corrupt_prob}")
    print(f"Delay prob: {delay_prob}")
    print("=" * 65)
 
    reset_sr_receiver(win_size=win_size)
 
    channel = UnreliableChannel(loss_prob, corrupt_prob, delay_prob)
    sender  = SRSender(channel, win_size=win_size)
 
    data_list = []
    for i in range(pkt_count):
        data = f"PKT{i:02d}" + ("X" * max(0, pkt_size - 5))
        data_list.append(data[:pkt_size])
 
    sender.send_all(data_list)
 
    print("\n" + "=" * 65)
    print("simulation Completed")
    print("=" * 65)
    print(f"PKTs ACKed: {sender.sent_count}/{pkt_count}")
    print(f"Total retransmissions: {sender.retry_count}")
    print(f"Data delivered (order):")
    for idx, d in enumerate(_sr_receiver_state["received_data"]):
        print(f"    [{idx}] {d}")
    print("=" * 65)
 
 
# =============================================================================
# ENTRY POINT
# =============================================================================
 
if __name__ == "__main__":
 
    print("\nSCENARIO 1: no issues")
    run_sr(pkt_count=5, win_size=3,
           loss_prob=0.0, corrupt_prob=0.0, delay_prob=0.0)
 
    print("\nSCENARIO 2: PKT loss")
    run_sr(pkt_count=5, win_size=3,
           loss_prob=0.4, corrupt_prob=0.0, delay_prob=0.0)
 
    print("\nSCENARIO 3: Corruption only")
    run_sr(pkt_count=5, win_size=3,
           loss_prob=0.0, corrupt_prob=0.4, delay_prob=0.0)
 
    print("\nSCENARIO 4: All conditions")
    run_sr(pkt_count=5, win_size=3,
           loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2)