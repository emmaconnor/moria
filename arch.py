from enum import Enum


class Endianness(Enum):
    LITTLE = 0
    BIG = 1


class Arch:
    endianness: Endianness
    char_size: int
    short_size: int
    int_size: int
    long_size: int
    long_long_size: int
    pointer_size: int

    def __init__(self, endianness: Endianness, word_size: int):
        self.endianness = endianness
        assert word_size in (4, 8), "Invalid word size"

        self.char_size = 1
        self.short_size = 2
        self.long_long_size = 8
        self.pointer_size = word_size

        if word_size == 4:
            self.int_size = 4
            self.long_size = 4
        elif word_size == 8:
            self.int_size = 4
            self.long_size = 8
