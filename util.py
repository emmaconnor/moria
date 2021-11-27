from typing import Callable, Iterator, Generic, TypeVar, List

T = TypeVar('T')


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

        assert(0 <= min_index <= len(self.elements))
        self.elements.insert(min_index, elem)
        return min_index

    def __iter__(self) -> Iterator[T]:
        return (elem for elem in self.elements)
