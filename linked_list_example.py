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

    user1 = namespace.user()
    user2 = namespace.user()

    user1.id = 1
    user1.name = "alice"
    user1.next = user2.ref()
    user1.prev = user2.ref()

    user2.id = 2
    user2.name = "bob"
    user2.next = user1.ref()
    user2.prev = user1.ref()

    start_address = 0x560A61DF4000
    packed = namespace.pack_values(start_address, 0x1000, [user1, user2])
    hexdump(packed, start_address=start_address)

    return 0


if __name__ == "__main__":
    sys.exit(main())
