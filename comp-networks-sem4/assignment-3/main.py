from rdt30 import run_rdt30
from gbn   import run_gbn
from sr    import run_sr

# HELPER FUNCS
def print_banner():
    print("\n" + "=" * 65)
    print("CS3001 - Computer Networks  |  Assignment #3")
    print("Reliable Data Transfer Protocols Simulator")
    print("Protocols: rdt 3.0  |  Go-Back-N  |  Selective Repeat")
    print("=" * 65)
 
def print_menu():
    print("\n  Select an option:")
    print("[1] rdt 3.0 — Stop-and-Wait")
    print("[2] GBN — Go-Back-N")
    print("[3] SR — Selective Repeat")
    print("[4] Run ALL protocols with ALL 4 test scenarios")
    print("[5] Exit")
    print()
 
def print_scenario_menu():
    print("\n  Select scenario:")
    print("[1] Clean — no loss, no corruption, no delay")
    print("[2] Packet Loss — loss only")
    print("[3] Corruption — corruption only")
    print("[4] All Conditions — loss + corruption + delay")
    print("[5] Custom — enter your own parameters")
    print()


def get_int(prompt, default):
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        return int(val) if val else default
    except ValueError:
        print(f"  Invalid input. Using default: {default}")
        return default
 
def get_float(prompt, default):
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        f   = float(val) if val else default
        return max(0.0, min(1.0, f))
    except ValueError:
        print(f"  Invalid input. Using default: {default}")
        return default
 
def get_custom_params(needs_window=False):
    print("\n  --- Configure Parameters ---")
    params = {
        "packet_count": get_int("Number of packets to send", 6),
        "packet_size": get_int("Packet size (characters)", 10),
        "loss_prob": get_float("Loss probability (0.0–1.0)", 0.2),
        "corrupt_prob": get_float("Corruption probability (0.0–1.0)", 0.2),
        "delay_prob": get_float("Delay probability (0.0–1.0)", 0.1),
    }
    if needs_window:
        params["window_size"] = get_int("Window size N", 4)
    return params