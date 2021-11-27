import sys
import argparse
from parsers.dwarf import DwarfParser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str,
                        help="display a square of a given number")
    parser.add_argument("-v", "--verbosity", action="count",
                        default=0, help="increase output verbosity")
    args = parser.parse_args()
    with open(args.filename, 'rb') as f:
        parser = DwarfParser(f)
        namespace = parser.get_structs()
        namespace.print_structs()


if __name__ == '__main__':
    main()
