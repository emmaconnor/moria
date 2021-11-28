import sys
from parsers.dwarf import DwarfParser
from util import hexdump

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
    )
    user2 = namespace.user(
        id=2,
        name="bob",
        next=user1.ref(),
        prev=user1.ref(),
    )

    user1.next = user2.ref()
    user1.prev = user2.ref()

    i = namespace.UInt32(0xDEADBEEF)

    start_address = 0x560A61DF4000
    packed = namespace.pack_values(start_address, 0x1000, [user1, user2, i])
    hexdump(packed, start_address=start_address)

    return 0


if __name__ == "__main__":
    sys.exit(main())
