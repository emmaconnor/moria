from moria.namespace import Namespace
from moria.arch import Arch, Endianness
from typing import Iterable

def make_namespaces() -> Iterable[Namespace]:
    endians = (Endianness.LITTLE, Endianness.BIG)
    word_sizes = (4, 8)
    for endian in endians:
        for word_size in word_sizes:
            yield make_namespace(endian, word_size)


def amd64_namespace() -> Namespace:
    return make_namespace(Endianness.LITTLE, 8)


def make_namespace(endian: Endianness, word_size: int) -> Namespace:
    return Namespace(arch=Arch(endianness=endian, word_size=word_size))