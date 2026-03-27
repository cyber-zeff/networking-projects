import socket
import sys
from dns_message import (DNSMessage, DNSFlags, DNSQuestion, DNSRecord, QTYPE_A, QTYPE_ANY, QTYPE_NAMES)

LOCAL_DNS_ADDR = ("127.0.0.1", 8353)
TIMEOUT = 5.0

def query(domain: str, qtype: int = QTYPE_ANY) -> DNSMessage:
    msg = DNSMessage()
    msg.flags = DNSFlags(qr=0, rd=1)
    msg.questions.append(DNSQuestion(domain, qtype))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(msg.to_bytes(), LOCAL_DNS_ADDR)
        data, _ = sock.recvfrom(4096)
        return DNSMessage.from_bytes(data)
    except socket.timeout:
        print(f"[CLIENT] ✗ Request timed out — is local_dns.py running?")
        sys.exit(1)
    finally:
        sock.close()

def print_dns_info(domain: str, response: DNSMessage):
    if response.flags.rcode == 3:
        print(f"\n{domain} — NXDOMAIN (domain does not exist)\n")
        return

    if response.flags.rcode != 0:
        print(f"\n{domain} — ERROR (rcode={response.flags.rcode})\n")
        return

    from_cache = any(r.rdata == "CACHE_HIT" for r in response.additional)
    if from_cache:
        print(f"[CLIENT] !! Served from LOCAL DNS cache — no chain traversal needed")

    a_records  = [r for r in response.answers if r.rtype == 1] 
    ns_records = [r for r in response.answers if r.rtype == 2] 
    mx_records = [r for r in response.answers if r.rtype == 15]

    primary_ip = a_records[0].rdata if a_records else "N/A"

    print(f"\n{domain}/{primary_ip}")
    print("-- DNS INFORMATION --")

    if a_records:
        ips = ", ".join(r.rdata for r in a_records)
        print(f"A: {ips}")

    if ns_records:
        ns = ", ".join(r.rdata + "." for r in ns_records)
        print(f"NS: {ns}")

    if mx_records:
        mx = ", ".join(r.rdata + "." for r in mx_records)
        print(f"MX: {mx}")

    if not (a_records or ns_records or mx_records):
        print("(No records returned)")

    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <domain> [domain2 ...]")
        print("Example: python client.py google.com github.com")
        sys.exit(0)

    domains = sys.argv[1:]

    for domain in domains:
        domain = domain.strip().lower()
        print(f"[CLIENT] Querying '{domain}' ...")

        response = query(domain, QTYPE_ANY)
        print_dns_info(domain, response)

if __name__ == "__main__":
    main()