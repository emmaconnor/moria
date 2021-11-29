import sys
from parsers.dwarf import DwarfParser
from util import hexdump
from values import TypedStructValue
from typing import List

EXAMPLE_BIN_PATH = "examples/userlist.bin"


def main():
    try:
        with open(EXAMPLE_BIN_PATH, "rb") as binary:
            namespace = DwarfParser(binary).parse()
    except FileNotFoundError:
        print(f"Binary {EXAMPLE_BIN_PATH} not found. Try building it first?")
        return 1

    users: List[TypedStructValue] = [
        namespace.user(
            name="alice",
        ),
        namespace.user(
            name="bob",
        ),
        namespace.user(
            name="charlie",
        ),
    ]

    for i in range(len(users)):
        user = users[i]
        prev_user = users[(i - 1) % len(users)]
        next_user = users[(i + 1) % len(users)]
        user.id = i + 1
        prev_user.next = user.ref()
        user.prev = prev_user.ref()
        next_user.prev = user.ref()
        user.next = next_user.ref()

    start_address = 0x560A61DF4000
    packed = namespace.pack_values(start_address, 0x1000, users)
    hexdump(packed, start_address=start_address)

    for user in users:
        print(user)

    return 0


if __name__ == "__main__":
    sys.exit(main())
