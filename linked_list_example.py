from parsers.dwarf import DwarfParser
from util import hexdump

EXAMPLE_BIN_PATH = "example/a.out"


def main():
    with open(EXAMPLE_BIN_PATH, "rb") as binary:
        namespace = DwarfParser(binary).parse()

    user1 = namespace.user()
    user2 = namespace.user()

    user1.id = 1
    user1.name = "alice"
    user1.next = user2.get_pointer()
    user1.prev = user2.get_pointer()

    user2.id = 2
    user2.name = "bob"
    user2.next = user1.get_pointer()
    user2.prev = user1.get_pointer()

    start_address = 0x560A61DF4000
    packed = namespace.pack_values(start_address, 0x1000, [user1, user2])
    hexdump(packed, start_address=start_address)


if __name__ == "__main__":
    main()
