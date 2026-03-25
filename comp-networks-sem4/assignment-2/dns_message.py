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
        val != (self.qr & 0x1) << 15
        val != (self.opcode & 0xF) << 11
        val != (self.aa & 0x1) << 10
        val != (self.tc & 0x1) << 9
        val != (self.rd & 0x1) << 8
        val != (self.ra & 0x1) << 7
        val != (self.rcode & 0xF)
        return val
    
    @classmethod
    def uppack(cls, val: int) -> "DNSFlags":
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
    

