import struct
import random

class DNSFlags:
    def __init__(self, qr=0, opcode=0, aa=0, tc=0, rd=0, ra=0, rcode=0):
        self.qr = qr
        self.opcode = opcode
        self.aa = aa
        self.tc = tc
        self.rd = rd
        self.ra = ra
        self.rcode = rcode

    def pack(self) -> int:
        val = 0
        val |= (self.qr & 0x1) << 15
        val |= (self.opcode & 0xF) << 11
        val |= (self.aa & 0x1) << 10
        val |= (self.tc & 0x1) << 9
        val |= (self.rd & 0x1) << 8
        val |= (self.ra & 0x1) << 7
        val |= (self.rcode & 0xF)
        return val
    
    @classmethod
    def unpack(cls, val: int) -> "DNSFlags":
        f = cls()
        f.qr = (val >> 15) & 0x1
        f.opcode = (val >> 11) & 0xF
        f.aa = (val >> 10) & 0x1
        f.tc = (val >> 9) & 0x1
        f.rd = (val >> 8) & 0x1
        f.ra = (val >> 7) & 0x1
        f.rcode = val & 0xF
        return f
    
    def __repr__(self):
        return (f"DNSFlags(qr={self.qr}, aa={self.aa}, "
                f"rd={self.rd}, ra={self.ra}, rcode={self.rcode})")
    

# dns record types
QTYPE_A = 1
QTYPE_NS = 2
QTYPE_MX = 15
QTYPE_ANY = 255

QTYPE_NAMES = {
    QTYPE_A: "A",
    QTYPE_NS: "NS",
    QTYPE_MX: "MX",
    QTYPE_ANY: "ANY",
}


# dns question sec
class DNSQuestion:
    def __init__(self, qname: str, qtype: int = QTYPE_A, qclass: int = 1):
        self.qname = qname.lower().strip(".")
        self.qtype = qtype
        self.qclass = qclass
    
    def __repr__(self):
        return (f"DNSQuestion(qname:'{self.qname}', "
                f"qtype={QTYPE_NAMES.get(self.qtype, self.qtype)})")
    

# dns resource record (RR)
class DNSRecord:
    def __init__(self, name: str, rtype: int, rdata: str, ttl: int = 300, rclass: int = 1):
        self.name = name.lower().strip(".")
        self.rtype = rtype
        self.rclass = rclass
        self.ttl = ttl
        self.rdata = rdata

    def __repr__(self):
        tname = QTYPE_NAMES.get(self.rtype, self.rtype)
        return f"DNSRecord({tname} {self.name} -> {self.rdata} [ttl={self.ttl}])"
    


HEADER_FORMAT = "!HHHHHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class DNSMessage:
    def __init__(self, msg_id: int = None, flags: DNSFlags = None, questions: list = None,
                 answers: list = None, authority: list = None, additional: list = None):
        self.msg_id = msg_id if msg_id is not None else random.randint(0, 0xFFFF)
        self.flags = flags or DNSFlags()
        self.questions = questions or []
        self.answers = answers or []
        self.authority = authority or []
        self.additional = additional or []

    # serialization (mes to raw net packets)
    def to_bytes(self) -> bytes:
        header = struct.pack(
            HEADER_FORMAT, self.msg_id, self.flags.pack(), len(self.questions), 
            len(self.answers), len(self.authority), len(self.additional),
        )

        body = self._encode_body()
        return header + body.encode()
    
    def _encode_body(self) -> str:
        parts = []
        for q in self.questions:
            parts.append(f"Q:{q.qname}:{q.qtype}:{q.qclass}")
        for rr in self.answers:
            parts.append(f"AN:{rr.name}:{rr.rtype}:{rr.ttl}:{rr.rdata}")
        for rr in self.authority:
            parts.append(f"NS:{rr.name}:{rr.rtype}:{rr.ttl}:{rr.rdata}")
        for rr in self.additional:
            parts.append(f"AR:{rr.name}:{rr.rtype}:{rr.ttl}:{rr.rdata}")
        return "|".join(parts)
    
    # deserialization
    @classmethod
    def from_bytes(cls, data: bytes) -> "DNSMessage":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Packer too short: {len(data)} bytes")
        
        raw_id, raw_flags, qdcount, ancount, nscount, arcount = \
            struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        
        msg = cls(
            msg_id = raw_id,
            flags = DNSFlags.unpack(raw_flags),
        )

        body = data[HEADER_SIZE:].decode(errors="replace")
        fields = body.split("|") if body else []

        for field in fields:
            if not field:
                continue
            parts = field.split(":")
            tag = parts[0]

            if tag == "Q" and len(parts) >= 4:
                msg.questions.append(
                    DNSQuestion(parts[1], int(parts[2]), int(parts[3]))
                )
            elif tag == "AN" and len(parts) >= 5:
                msg.answers.append(
                    DNSRecord(parts[1], int(parts[2]), parts[4], int(parts[3]))
                )
            elif tag == "NS" and len(parts) >= 5:
                msg.authority.append(
                    DNSRecord(parts[1], int(parts[2]), parts[4], int(parts[3]))
                )
            elif tag == "AR" and len(parts) >= 5:
                msg.additional.append(
                    DNSRecord(parts[1], int(parts[2]), parts[4], int(parts[3]))
                )
        
        return msg
    

    def pretty(self) -> str:
        lines = []
        lines.append("=" * 48)
        lines.append(f"  DNS MESSAGE  ID=0x{self.msg_id:04X}  "
                     f"({'RESPONSE' if self.flags.qr else 'QUERY'})")
        lines.append(f"  Flags : {self.flags}")
        lines.append(f"  QD={len(self.questions)}  AN={len(self.answers)}  "
                     f"NS={len(self.authority)}  AR={len(self.additional)}")
        lines.append("-" * 48)
 
        if self.questions:
            lines.append("  QUESTION SECTION:")
            for q in self.questions:
                lines.append(f"    {q.qname}  {QTYPE_NAMES.get(q.qtype,'?')}")
 
        if self.answers:
            lines.append("  ANSWER SECTION:")
            for rr in self.answers:
                lines.append(f"    {rr.name}  {QTYPE_NAMES.get(rr.rtype,'?')}  "
                             f"{rr.rdata}  ttl={rr.ttl}")
 
        if self.authority:
            lines.append("  AUTHORITY SECTION:")
            for rr in self.authority:
                lines.append(f"    {rr.name}  {QTYPE_NAMES.get(rr.rtype,'?')}  "
                             f"{rr.rdata}  ttl={rr.ttl}")
 
        if self.additional:
            lines.append("  ADDITIONAL SECTION:")
            for rr in self.additional:
                lines.append(f"    {rr.name}  {QTYPE_NAMES.get(rr.rtype,'?')}  "
                             f"{rr.rdata}  ttl={rr.ttl}")
 
        lines.append("=" * 48)
        return "\n".join(lines)
 
    
    def __repr__(self):
        return (f"DNSMessage(id=0x{self.msg_id:04X}, "
                f"qr={self.flags.qr}, "
                f"questions={self.questions}, "
                f"answers={self.answers})")
    
