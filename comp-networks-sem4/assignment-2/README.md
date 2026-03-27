# DNS Resolver Simulation

A simulated DNS resolution system built using Python sockets for my Computer Networks course (Semester 4).

## What It Does

This project simulates the complete DNS resolution chain with multiple server types:
- **Root Server** - Directs queries to appropriate TLD servers
- **TLD Server** - Directs queries to authoritative name servers
- **Authoritative Server** - Returns actual DNS records for domains
- **Local DNS Resolver** - Performs iterative resolution with caching
- **Client** - Sends DNS queries and displays results

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │ ──> │  Local DNS  │ ──> │    Root     │ ──> │    TLD      │
│  client.py  │     │ local_dns.py│     │root_server.py│     │tld_server.py│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                                       │
                           │                                       │
                           │                                       v
                           │                               ┌─────────────┐
                           │                               │  Authoritative│
                           │                               │ auth_server.py│
                           │                               └─────────────┘
                           │
                    ┌─────────────┐
                    │   Cache     │
                    │ (5 entries, │
                    │  60s TTL)   │
                    └─────────────┘
```

## Server Ports

| Server | Port | Description |
|--------|------|-------------|
| Root | 5300 | Root DNS server |
| TLD | 5301 | Top-Level Domain server |
| Authoritative | 5302 | Authoritative name server |
| Local DNS | 8353 | Local resolver (client connects here) |

## Features

- **Iterative Resolution** - Local DNS performs Root → TLD → Auth chain
- **DNS Caching** - Local DNS caches up to 5 entries with 60s TTL (LRU eviction)
- **Multiple Record Types** - Supports A, NS, MX, and ANY queries
- **Zone Database** - Pre-configured domains with realistic DNS records
- **Error Handling** - Proper NXDOMAIN and timeout responses

## Supported Domains

| Domain | IPs |
|--------|-----|
| google.com | 64.233.187.99, 72.14.207.99, 64.233.167.99 |
| github.com | 140.82.121.4, 140.82.121.3 |
| youtube.com | 142.250.80.78, 142.250.80.46 |
| facebook.com | 157.240.241.35, 157.240.19.35 |
| amazon.com | 205.251.242.103, 54.239.28.85, 54.239.17.6 |
| microsoft.com | 20.112.52.29, 20.81.111.85 |
| stackoverflow.com | 151.101.1.69, 151.101.65.69 |
| wikipedia.org | 208.80.154.224, 208.80.153.224 |
| umass.edu | 128.119.240.10, 128.119.240.19 |
| mit.edu | 18.9.22.169 |
| stanford.edu | 171.67.215.200 |
| nu.edu.pk | 119.63.132.100 |
| fast.edu.pk | 119.63.132.101 |
| github.io | 185.199.108.153, 185.199.109.153 |

## How to Run

Open 5 terminals and run in this order:

```bash
# Terminal 1
python root_server.py

# Terminal 2
python tld_server.py

# Terminal 3
python auth_server.py

# Terminal 4
python local_dns.py

# Terminal 5 — your queries
python client.py google.com
python client.py github.com
python client.py google.com   # ← this one hits cache, no chain
```

## How It Works

1. **Client** sends DNS query to Local DNS resolver (port 8353)
2. **Local DNS** first checks its cache:
   - **Cache HIT** → Returns cached result immediately (no chain traversal)
   - **Cache MISS** → Starts iterative resolution
3. **Iterative Resolution** (on cache miss):
   - Query **Root Server** (port 5300) → Returns TLD server referral
   - Query **TLD Server** (port 5301) → Returns Auth server referral
   - Query **Auth Server** (port 5302) → Returns actual DNS records
4. **Local DNS** caches the result and responds to client
5. Subsequent queries for same domain within 60s are served from cache

## DNS Message Format

Custom DNS message encoding/decoding implemented in `dns_message.py`:
- **Header**: Message ID, flags (QR, AA, RD, RA, RCODE), section counts
- **Question Section**: Domain name, query type
- **Answer/Authority/Additional Sections**: Resource records (name, type, TTL, data)

## Record Types

| Type | Code | Description |
|------|------|-------------|
| A | 1 | IPv4 Address |
| NS | 2 | Name Server |
| MX | 15 | Mail Exchange |
| ANY | 255 | All Records |

## Limitations

- Only supports iterative queries (no recursive)
- Zone data is hardcoded (no dynamic updates)
- No support for CNAME, TXT, AAAA records
- Single-threaded servers
- No DNSSEC support

---
**Course:** Computer Networks | **Semester:** 4 | **Assignment:** 2
