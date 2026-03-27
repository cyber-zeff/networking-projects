import socket
from dns_message import (DNSMessage, DNSFlags, DNSRecord, QTYPE_A, QTYPE_NS, QTYPE_MX, QTYPE_ANY)

HOST = "127.0.0.1"
PORT = 5302


ZONE_DB = {
    "google.com": {
        QTYPE_A : ["64.233.187.99", "72.14.207.99", "64.233.167.99"],
        QTYPE_NS: ["ns1.google.com", "ns2.google.com",
                   "ns3.google.com", "ns4.google.com"],
        QTYPE_MX: ["10 smtp1.google.com", "10 smtp2.google.com",
                   "10 smtp3.google.com", "10 smtp4.google.com"],
    },
    "youtube.com": {
        QTYPE_A : ["142.250.80.78", "142.250.80.46"],
        QTYPE_NS: ["ns1.youtube.com", "ns2.youtube.com"],
        QTYPE_MX: ["10 mail.youtube.com"],
    },
    "facebook.com": {
        QTYPE_A : ["157.240.241.35", "157.240.19.35"],
        QTYPE_NS: ["a.ns.facebook.com", "b.ns.facebook.com"],
        QTYPE_MX: ["10 smtpin.vvv.facebook.com"],
    },
    "amazon.com": {
        QTYPE_A : ["205.251.242.103", "54.239.28.85", "54.239.17.6"],
        QTYPE_NS: ["ns1.p31.dynect.net", "ns2.p31.dynect.net"],
        QTYPE_MX: ["10 smtp.amazon.com"],
    },
    "microsoft.com": {
        QTYPE_A : ["20.112.52.29", "20.81.111.85"],
        QTYPE_NS: ["ns1.msft.net", "ns2.msft.net"],
        QTYPE_MX: ["10 microsoft-com.mail.protection.outlook.com"],
    },
    "github.com": {
        QTYPE_A : ["140.82.121.4", "140.82.121.3"],
        QTYPE_NS: ["ns-1283.awsdns-32.org", "ns-1707.awsdns-21.co.uk"],
        QTYPE_MX: ["1 aspmx.l.google.com", "5 alt1.aspmx.l.google.com"],
    },
    "stackoverflow.com": {
        QTYPE_A : ["151.101.1.69", "151.101.65.69"],
        QTYPE_NS: ["ns1.stackoverflow.com", "ns2.stackoverflow.com"],
        QTYPE_MX: ["10 aspmx.l.google.com"],
    },
    "wikipedia.org": {
        QTYPE_A : ["208.80.154.224", "208.80.153.224"],
        QTYPE_NS: ["ns0.wikimedia.org", "ns1.wikimedia.org"],
        QTYPE_MX: ["10 mx1001.wikimedia.org"],
    },
    "umass.edu": {
        QTYPE_A : ["128.119.240.10", "128.119.240.19"],
        QTYPE_NS: ["ns1.umass.edu", "ns2.umass.edu"],
        QTYPE_MX: ["10 smtp.umass.edu"],
    },
    "mit.edu": {
        QTYPE_A : ["18.9.22.169"],
        QTYPE_NS: ["ns1.mit.edu", "ns2.mit.edu"],
        QTYPE_MX: ["10 mit-edu.mail.protection.outlook.com"],
    },
    "stanford.edu": {
        QTYPE_A : ["171.67.215.200"],
        QTYPE_NS: ["avallone.stanford.edu", "argus.stanford.edu"],
        QTYPE_MX: ["10 smtp.stanford.edu"],
    },
    "nu.edu.pk": {
        QTYPE_A : ["119.63.132.100"],
        QTYPE_NS: ["ns1.nu.edu.pk", "ns2.nu.edu.pk"],
        QTYPE_MX: ["10 mail.nu.edu.pk"],
    },
    "fast.edu.pk": {
        QTYPE_A : ["119.63.132.101"],
        QTYPE_NS: ["ns1.fast.edu.pk"],
        QTYPE_MX: ["10 mail.fast.edu.pk"],
    },
    "github.io": {
        QTYPE_A : ["185.199.108.153", "185.199.109.153"],
        QTYPE_NS: ["ns-1622.awsdns-10.co.uk"],
        QTYPE_MX: [],
    },
}


def resolve(qname: str, qtype: int) -> list:
    qname = qname.strip(".")
    parts = qname.split(".")

    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in ZONE_DB:
            zone = ZONE_DB[candidate]
            if qtype == QTYPE_ANY:
                all_records = []
                for rtype, rdata_list in zone.items():
                    for rdata in rdata_list:
                        all_records.append((rtype, rdata))
                return all_records
            return [(qtype, r) for r in zone.get(qtype, [])]
    
    return []


def handle_query(msg: DNSMessage) -> DNSMessage:
    response = DNSMessage(msg_id=msg.msg_id)
    response.flags = DNSFlags(qr=1, aa=1, rd=msg.flags.rd, ra=0, rcode=0)
    response.questions = msg.questions

    if not msg.questions:
        response.flags.rcode = 2 # servfail
        return response
    
    qname = msg.questions[0].qname
    qtype = msg.questions[0].qtype

    print(f"[AUTH] Query for '{qname}' type={qtype}")
    records = resolve(qname, qtype)

    if not records:
        print(f"[AUTH] No records found for '{qname}' - NXDOMAIN")
        response.flags.rcode = 3 # nxdomain
        return response
    
    for rtype, rdata in records: 
        response.answers.append(
            DNSRecord(qname, rtype, rdata, ttl=300)
        )

    if qtype != QTYPE_NS:
        ns_records = resolve(qname, QTYPE_NS)
        for _, rdata in ns_records:
            response.authority.append(
                DNSRecord(qname, QTYPE_NS, rdata, ttl=86400)
            )
    
    print(f"[AUTH] Returning {len(response.answers)} answer(s) for '{qname}'")
    return response

def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[AUTH] Authoritative DNS server listening on {HOST}:{PORT}")
    print(f"[AUTH] Authoritation for: {list(ZONE_DB.keys())}\n")

    while True:
        data, addr = sock.recvfrom(4096)
        print(f"[AUTH] Received query from {addr}")
        try:
            msg = DNSMessage.from_bytes(data)
            print(msg.pretty())
            response = handle_query(msg)
            print(response.pretty())
            sock.sendto(response.to_bytes(), addr)
        except Exception as e:
            print(f"[AUTH] Error: {e}")


if __name__ == "__main__":
    run()