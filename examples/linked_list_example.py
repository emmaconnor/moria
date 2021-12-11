import sys

from typing import List

try:
    from moria.parsers.dwarf import DwarfParser
    from moria.util import hexdump
    from moria.values import StructValue
except ImportError:
    # In case moria is not installed, add the parent folder to the module
    # search path so that it's still possible to run this script from the
    # examples directory.
    sys.path.append("..")
    from moria.parsers.dwarf import DwarfParser
    from moria.util import hexdump
    from moria.values import StructValue

EXAMPLE_BIN_PATH = "cprograms/userlist.bin"


def main():
    try:
        with open(EXAMPLE_BIN_PATH, "rb") as binary:
            ns = DwarfParser(binary).create_namespace()
    except FileNotFoundError:
        print(f"Binary {EXAMPLE_BIN_PATH} not found. Try building it first?")
        return 1

    users: List[StructValue] = [
        ns.user(name="alice"),
        ns.user(name="bob"),
        ns.user(name="charlie"),
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

    start_address = 0x560000000000
    packed = ns.pack_values(start_address, 0x1000, users)
    hexdump(packed, start_address=start_address)

    unpacked_users = ns.array(ns.user, 3).unpack_from_buffer(
        packed, offset=start_address
    )

    for user in unpacked_users.values:
        assert isinstance(user, StructValue)
        print(user)

    return 0


if __name__ == "__main__":
    sys.exit(main())
