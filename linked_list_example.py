import sys
from parsers.dwarf import DwarfParser
from util import hexdump
from values import BufferValue

EXAMPLE_BIN_PATH = "examples/userlist.bin"


def main():
    try:
        with open(EXAMPLE_BIN_PATH, "rb") as binary:
            namespace = DwarfParser(binary).parse()
    except FileNotFoundError:
        print(f"Binary {EXAMPLE_BIN_PATH} not found. Try building it first?")
        return 1

    user1 = namespace.user(
        id=1,
        name="alice",
        next=0xDEADBEEF,
        prev=0xDEADBEEF,
    )
    user2 = namespace.user(
        id=2,
        name=list(b"bob"),
        next=user1.ref(),
        prev=user1.ref(),
    )

    user1.next = user2.ref()
    user1.prev = user2.ref()

    user_ptrs = BufferValue([user1.ref(), user2.ref()])

    i = namespace.UInt32(0xCAFEBABE)

    start_address = 0x560A61DF4000
    packed = namespace.pack_values(start_address, 0x1000, [i, user_ptrs])
    hexdump(packed, start_address=start_address)

    return 0


if __name__ == "__main__":
    sys.exit(main())
