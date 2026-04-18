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


# example runs
def run_protocol_menu(protocol_name, run_func, needs_window=False):
    default_window = 4
 
    while True:
        print(f"\n  Protocol: {protocol_name}")
        print_scenario_menu()
        choice = input("  Your choice: ").strip()
 
        # Scenario 1 -- Perfect scenario
        if choice == "1":
            args = dict(packet_count=6, packet_size=10,
                        loss_prob=0.0, corrupt_prob=0.0, delay_prob=0.0)
            if needs_window:
                args["window_size"] = default_window
            run_func(**args)
 
        # Scenario 2 -- Loss only
        elif choice == "2":
            args = dict(packet_count=6, packet_size=10,
                        loss_prob=0.4, corrupt_prob=0.0, delay_prob=0.0)
            if needs_window:
                args["window_size"] = default_window
            run_func(**args)
 
        # Scenario 3 -- Corruption only
        elif choice == "3":
            args = dict(packet_count=6, packet_size=10,
                        loss_prob=0.0, corrupt_prob=0.4, delay_prob=0.0)
            if needs_window:
                args["window_size"] = default_window
            run_func(**args)
 
        # Scenario 4 -- All conditions
        elif choice == "4":
            args = dict(packet_count=6, packet_size=10,
                        loss_prob=0.3, corrupt_prob=0.3, delay_prob=0.2)
            if needs_window:
                args["window_size"] = default_window
            run_func(**args)
 
        # Scenario 5 -- Custom
        elif choice == "5":
            params = get_custom_params(needs_window=needs_window)
            run_func(**params)
 
        else:
            print("  Invalid choice.")
 
        again = input("\nRun another scenario for this protocol? (y/n): ").strip().lower()
        if again != "y":
            break


def run_all_protocols():
    PACKET_COUNT = 5
    PACKET_SIZE  = 10
    WINDOW_SIZE  = 3
 
    scenarios = [
        ("SCENARIO 1: no issues", 0.0, 0.0, 0.0),
        ("SCENARIO 2: PKT Loss only", 0.4, 0.0, 0.0),
        ("SCENARIO 3: Corruption only", 0.0, 0.4, 0.0),
        ("SCENARIO 4: All conditions", 0.3, 0.3, 0.2),
    ]
 
    print("\n" + "=" * 65)
    print("FULL DEMO — All 3 Protocols x All 4 Scenarios")
    print(f"Packet count={PACKET_COUNT}, Packet size={PACKET_SIZE}, "
          f"Window N={WINDOW_SIZE}")
    print("=" * 65)
 
    for label, loss, corrupt, delay in scenarios:
 
        print(f"\n{'#' * 65}")
        print(f"{label}")
        print(f"loss={loss}  corrupt={corrupt}  delay={delay}")
        print(f"{'#' * 65}")
 
        # -- rdt 3.0
        print(f"\n{'─' * 65}")
        print("PROTOCOL: rdt 3.0 (Stop-and-Wait)")
        print(f"{'─' * 65}")
        run_rdt30(packet_count=PACKET_COUNT, packet_size=PACKET_SIZE,
                  loss_prob=loss, corrupt_prob=corrupt, delay_prob=delay)
 
        # -- GBN
        print(f"\n{'─' * 65}")
        print("PROTOCOL: Go-Back-N")
        print(f"{'─' * 65}")
        run_gbn(packet_count=PACKET_COUNT, packet_size=PACKET_SIZE,
                window_size=WINDOW_SIZE,
                loss_prob=loss, corrupt_prob=corrupt, delay_prob=delay)
 
        # -- SR
        print(f"\n{'─' * 65}")
        print("PROTOCOL: Selective Repeat")
        print(f"{'─' * 65}")
        run_sr(packet_count=PACKET_COUNT, packet_size=PACKET_SIZE,
               window_size=WINDOW_SIZE,
               loss_prob=loss, corrupt_prob=corrupt, delay_prob=delay)
 
    print("\n" + "=" * 65)
    print("FULL DEMO COMPLETE")
    print("=" * 65)
 
 
def main():
    print_banner()
 
    while True:
        print_menu()
        choice = input("Your choice: ").strip()
 
        if choice == "1":
            run_protocol_menu("rdt 3.0 — Stop-and-Wait", run_rdt30, needs_window=False)
 
        elif choice == "2":
            run_protocol_menu("Go-Back-N (GBN)", run_gbn, needs_window=True)
 
        elif choice == "3":
            run_protocol_menu("Selective Repeat (SR)", run_sr, needs_window=True)
 
        elif choice == "4":
            run_all_protocols()
 
        elif choice == "5":
            print("\nExiting. Goodbye!\n")
            break
 
        else:
            print("Invalid choice. Please enter 1–5.")
 
 
if __name__ == "__main__":
    main()