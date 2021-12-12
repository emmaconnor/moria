from typing import Callable, Iterator, Generic, TypeVar, List


def hexdump(data: bytes, start_address: int = 0) -> None:
    chunk_size = 16
    group_size = 8
    for i in range(0, len(data), chunk_size):
        chunk = data[i: i + chunk_size]
        hex_bytes = [f"{byte:02x}" for byte in chunk]
        hex_chunks = []
        for j in range(0, len(chunk), group_size):
            hex_chunk = hex_bytes[j: j + group_size]
            hex_chunks.append(" ".join(hex_chunk))

        data_hex = "  ".join(hex_chunks)
        ascii = "".join([chr(i) if 32 <= i <= 127 else "." for i in chunk])
        print(f"{start_address+i:016x}  {data_hex:<48}  |{ascii}|")


T = TypeVar("T")


class SortedList(Generic[T]):
    def __init__(self, key: Callable[[T, T], int]):
        self.key = key
        self.elements: List[T] = []

    def insert(self, elem: T) -> int:
        min_index = 0
        max_index = len(self.elements)
        while min_index < max_index:
            midpoint = (max_index - min_index) // 2 + min_index
            compare_result = self.key(elem, self.elements[midpoint])
            if compare_result < 0:
                max_index = midpoint
            elif compare_result > 0:
                min_index = midpoint + 1
            else:
                max_index = midpoint
                min_index = midpoint

        assert 0 <= min_index <= len(self.elements)
        self.elements.insert(min_index, elem)
        return min_index

    def __getitem__(self, i: int) -> T:
        return self.elements[i]

    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> Iterator[T]:
        return (elem for elem in self.elements)
