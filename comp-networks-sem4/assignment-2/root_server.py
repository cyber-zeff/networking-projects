import socket
from dns_message import DNSMessage, DNSFlags, DNSQuestion, DNSRecord, QTYPE_NS, QTYPE_A


HOST = "127.0.0.1"
PORT = 5300

ROOT_ZONE = {
    "com" : ("tld.com-server", "127.0.0.1", 5301),
    "edu" : ("tld.edu-server", "127.0.0.1", 5301),
    "org" : ("tld.org-server", "127.0.0.1", 5301),
    "net" : ("tld.net-server", "127.0.0.1", 5301),
    "io" : ("tld.io-server", "127.0.0.1", 5301),
    "pk" : ("tld.pk-server", "127.0.0.1", 5301),
}


def get_tld(domain: str) -> str:
    parts = domain.strip(".").split(".")
    return parts[-1] if parts else ""

def handle_query(msg: DNSMessage) -> DNSMessage:
    response = DNSMessage(msg_id=msg.msg_id)
    response.flags = DNSFlags(qr=1, aa=0, rd=msg.flags.rd, ra=0, rcode=0)
    response.questions = msg.questions

    if not msg.questions:
        response.flags.rcode = 2 #servfail == server failure
        return response
    
    qname = msg.questions[0].qname
    tld = get_tld(qname)
    
    print(f"[ROOT] Query for '{qname}' -> TLD='{tld}'")

    if tld not in ROOT_ZONE:
        print(f"[ROOT] Unknown TLD '{tld}' - sending NXDOMAIN")
        response.flags.rcode = 3
        return response
    
    ns_name, tld_ip, tld_port = ROOT_ZONE[tld]

    response.authority.append(
        DNSRecord(f".{tld}", QTYPE_NS, ns_name, ttl=172800)
    )
    response.additional.append(
        DNSRecord(ns_name, QTYPE_A, f"{tld_ip}:{tld_port}", ttl=172800)
    )

    print(f"[ROOT] Refferring to TLD server '{ns_name}' @ {tld_ip}:{tld_port}")
    return response

def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind((HOST, PORT))
    print(f"[ROOT] Root DNS server listening on {HOST}:{PORT}")
    print(f"[ROOT] Knows TLDs: {list(ROOT_ZONE.keys())}\n")

    while True:
        data, addr = sock.recvfrom(4096)
        print(f"[ROOT] Received query from {addr}")
        try:
            msg = DNSMessage.from_bytes(data)
            print(msg.pretty())
            response = handle_query(msg)
            print(response.pretty())
            sock.sendto(response.to_bytes(), addr)
        except Exception as e:
            print(f"[ROOT] Error: {e}")

if __name__ == "__main__":
    run()