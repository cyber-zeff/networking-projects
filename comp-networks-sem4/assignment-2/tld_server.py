import socket
from dns_message import DNSMessage, DNSFlags, DNSRecord, QTYPE_NS, QTYPE_A
 
HOST = "127.0.0.1"
PORT = 5301


TLD_ZONE = {
    "google.com" : ("ns1.google.com", "127.0.0.1", 5302),
    "youtube.com" : ("ns1.youtube.com", "127.0.0.1", 5302),
    "facebook.com" : ("ns1.facebook.com", "127.0.0.1", 5302),
    "amazon.com" : ("ns1.amazon.com", "127.0.0.1", 5302),
    "microsoft.com" : ("ns1.microsoft.com", "127.0.0.1", 5302),
    "github.com" : ("ns1.github.com", "127.0.0.1", 5302),
    "stackoverflow.com" : ("ns1.stackoverflow.com", "127.0.0.1", 5302),

    "umass.edu" : ("ns1.umass.edu", "127.0.0.1", 5302),
    "mit.edu" : ("ns1.mit.edu", "127.0.0.1", 5302),
    "stanford.edu" : ("ns1.stanford.edu", "127.0.0.1", 5302),
    "nu.edu.pk" : ("ns1.nu.edu.pk", "127.0.0.1", 5302),

    "wikipedia.org" : ("ns1.wikipedia.org", "127.0.0.1", 5302),
 
    "github.io"     : ("ns1.github.io",         "127.0.0.1", 5302),
 
    "fast.edu.pk"   : ("ns1.fast.edu.pk",       "127.0.0.1", 5302),
}


def get_sld(domain: str) -> str:
    domain = domain.strip(".")
    parts = domain.split(".")

    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in TLD_ZONE:
            return candidate
    return domain

def handle_query(msg: DNSMessage) -> DNSMessage:
    response = DNSMessage(msg_id=msg.msg_id)
    response.flags = DNSFlags(qr=1, aa=0, rd=msg.flags.rd, ra=0, rcode=0)
    response.questions = msg.questions

    if not msg.questions:
        response.flags.rcode = 2 # server fail
        return response
    
    qname = msg.questions[0].qname
    domain = get_sld(qname)

    print(f"[TLD] Query for '{qname}'  →  domain='{domain}'")

    if domain not in TLD_ZONE:
        print(f"[TLD] Domain '{domain}' not found — sending NXDOMAIN")
        response.flags.rcode = 3 # NX domain
        return response
    
    ns_name, auth_ip, auth_port = TLD_ZONE[domain]

    response.authority.append(
        DNSRecord(domain, QTYPE_NS, ns_name, ttl=172800)
    )
    response.additional.append(
        DNSRecord(ns_name, QTYPE_A, f"{auth_ip}:{auth_port}", ttl=172800)
    )

    print(f"[TLD] Referring to auth server '{ns_name}' @ {auth_ip}:{auth_port}")
    return response


def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind((HOST, PORT))
    print(f"[TLD] TLD DNS server listening on {HOST}:{PORT}")
    print(f"[TLD] Knows domains: {list(TLD_ZONE.keys())}\n")

    while True:
        data, addr = sock.recvfrom(4096)
        print(f"[TLD] Received query from {addr}")
        try:
            msg = DNSMessage.from_bytes(data)
            print(msg.pretty())
            response = handle_query(msg)
            print(response.pretty())
            sock.sendto(response.to_bytes(), addr)
        except Exception as e:
            print(f"[TLD] Error: {e}")

if __name__ == "__main__":
    run()