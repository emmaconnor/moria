import argparse
import sys
from parsers.dwarf import DwarfParser

EXAMPLE_BIN_PATH = "examples/userlist.bin"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Binary file to read")
    args = parser.parse_args()
    try:
        with open(args.input, "rb") as binary:
            namespace = DwarfParser(binary).parse()
    except FileNotFoundError:
        print("File not found.")
        return 1

    namespace.print_structs()
    return 0


if __name__ == "__main__":
    sys.exit(main())
