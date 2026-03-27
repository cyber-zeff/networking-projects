import socket
import time
from collections import OrderedDict
from dns_message import (DNSMessage, DNSFlags, DNSRecord, DNSQuestion, QTYPE_A, QTYPE_NS, QTYPE_MX, QTYPE_ANY, QTYPE_NAMES)

HOST = "127.0.0.1"
PORT = 8353

# Server addresses
ROOT_ADDR = ("127.0.0.1", 5300)
TLD_ADDR  = ("127.0.0.1", 5301)
AUTH_ADDR = ("127.0.0.1", 5302)

# cache settings
CACHE_MAX = 5
CACHE_TTL = 60

cache: OrderedDict = OrderedDict()

def cache_store(qname: str, qtype: int, records: list):
    key = (qname.lower(), qtype)

    if key in cache:
        del cache[key]

    if len(cache) >= CACHE_MAX:
        evicted_key, _ = cache.popitem(last=False)
        print(f"[CACHE] !! Auto-flush: evicted '{evicted_key[0]}' "
              f"(type={QTYPE_NAMES.get(evicted_key[1], evicted_key[1])}) — cache was full")

    cache[key] = {
        "records": records,
        "expires": time.time() + CACHE_TTL,
    }
    print(f"[CACHE] Stored '{qname}' (type={QTYPE_NAMES.get(qtype, qtype)}) "
          f"— cache size now {len(cache)}/{CACHE_MAX}")

def cache_lookup(qname: str, qtype: int):
    key = (qname.lower(), qtype)
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() > entry["expires"]:
        del cache[key]
        print(f"[CACHE] '{qname}' expired — removed from cache")
        return None
    remaining = int(entry["expires"] - time.time())
    print(f"[CACHE] HIT for '{qname}' — {remaining}s remaining in cache")
    return entry["records"]

def cache_status():
    if not cache:
        print("[CACHE] Cache is empty")
        return
    print(f"[CACHE] Current cache ({len(cache)}/{CACHE_MAX} entries):")
    for (qname, qtype), entry in cache.items():
        remaining = max(0, int(entry["expires"] - time.time()))
        print(f"  • {qname:30s}  type={QTYPE_NAMES.get(qtype, qtype):<5}  "
              f"ttl_remaining={remaining}s  records={len(entry['records'])}")


def send_query(msg: DNSMessage, addr: tuple, timeout: float = 3.0) -> DNSMessage:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(msg.to_bytes(), addr)
        data, _ = sock.recvfrom(4096)
        return DNSMessage.from_bytes(data)
    finally:
        sock.close()


def iterative_resolve(qname: str, qtype: int) -> list:
    print(f"\n[LOCAL] -- Starting iterative resolution for '{qname}' --")

    query = DNSMessage()
    query.flags = DNSFlags(qr=0, rd=1)
    query.questions.append(DNSQuestion(qname, qtype))

    # 1. ask root
    print(f"[LOCAL] Step 1 → Querying ROOT server @ {ROOT_ADDR}")
    try:
        root_resp = send_query(query, ROOT_ADDR)
    except socket.timeout:
        print("[LOCAL] Root server timed out")
        return []

    if root_resp.flags.rcode != 0:
        print(f"[LOCAL] Root returned rcode={root_resp.flags.rcode} (NXDOMAIN/error)")
        return []

    tld_addr = _extract_addr(root_resp.additional, TLD_ADDR)
    print(f"[LOCAL] Root referred us to TLD @ {tld_addr}")

    # 2. ask tld
    print(f"[LOCAL] Step 2 → Querying TLD server @ {tld_addr}")
    try:
        tld_resp = send_query(query, tld_addr)
    except socket.timeout:
        print("[LOCAL] TLD server timed out")
        return []

    if tld_resp.flags.rcode != 0:
        print(f"[LOCAL] TLD returned rcode={tld_resp.flags.rcode} (NXDOMAIN/error)")
        return []

    auth_addr = _extract_addr(tld_resp.additional, AUTH_ADDR)
    print(f"[LOCAL] TLD referred us to AUTH @ {auth_addr}")

    # 3. ask authoritative
    print(f"[LOCAL] Step 3 → Querying AUTH server @ {auth_addr}")
    try:
        auth_resp = send_query(query, auth_addr)
    except socket.timeout:
        print("[LOCAL] Auth server timed out")
        return []

    if auth_resp.flags.rcode == 3:
        print(f"[LOCAL] AUTH says NXDOMAIN — domain does not exist")
        return []

    if auth_resp.flags.rcode != 0:
        print(f"[LOCAL] AUTH returned error rcode={auth_resp.flags.rcode}")
        return []

    print(f"[LOCAL] Got {len(auth_resp.answers)} answer(s) from AUTH")
    return auth_resp.answers


def _extract_addr(additional: list, fallback: tuple) -> tuple:
    for rr in additional:
        if ":" in rr.rdata:
            try:
                ip, port = rr.rdata.rsplit(":", 1)
                return (ip, int(port))
            except ValueError:
                pass
    return fallback


def handle_client(msg: DNSMessage) -> DNSMessage:
    response = DNSMessage(msg_id=msg.msg_id)
    response.flags = DNSFlags(qr=1, rd=1, ra=1, rcode=0)
    response.questions = msg.questions

    if not msg.questions:
        response.flags.rcode = 2
        return response

    qname = msg.questions[0].qname
    qtype = msg.questions[0].qtype

    print(f"\n{'='*55}")
    print(f"[LOCAL] Client query: '{qname}'  "
          f"type={QTYPE_NAMES.get(qtype, qtype)}")
    print(f"{'='*55}")

    cached = cache_lookup(qname, qtype)
    if cached:
        print(f"[LOCAL] CACHE HIT — serving from cache, skipping Root→TLD→Auth chain")
        response.answers = cached
        response.flags.aa = 0

        response.additional.append(
            DNSRecord(qname, 16, "CACHE_HIT", ttl=0)
        )
        cache_status()
        return response

    answers = iterative_resolve(qname, qtype)

    if not answers:
        print(f"[LOCAL] Resolution failed — NXDOMAIN")
        response.flags.rcode = 3
        cache_status()
        return response

    cache_store(qname, qtype, answers)
    response.answers = answers
    cache_status()
    return response


def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[LOCAL] Local DNS resolver listening on {HOST}:{PORT}")
    print(f"[LOCAL] Cache capacity: {CACHE_MAX} entries, TTL: {CACHE_TTL}s\n")

    while True:
        data, addr = sock.recvfrom(4096)
        try:
            msg      = DNSMessage.from_bytes(data)
            response = handle_client(msg)
            print(response.pretty())
            sock.sendto(response.to_bytes(), addr)
        except Exception as e:
            print(f"[LOCAL] Error: {e}")

if __name__ == "__main__":
    run()