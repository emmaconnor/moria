from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FreeChunk:
    address: int
    size: int

    @property
    def end(self):
        return self.address + self.size

    def split(self, address: int, size: int) -> List[FreeChunk]:
        end = address + size
        new_chunks: List[FreeChunk] = []
        if (address < self.address
                or end > self.end
                or size < 0):
            raise ValueError('Cannot split chunk {self} by allocating 0x{address:x}+{size}')
        if address > self.address:
            new_chunks.append(FreeChunk(self.address, address - self.address))
        if end < self.end:
            new_chunks.append(FreeChunk(end, self.end - end))
        return new_chunks


class HeapPacker:
    free_chunks: List[FreeChunk]

    def __init__(self, address: int, size: int) -> None:
        self.free_chunks = [FreeChunk(address, size)]

    def alloc(self, size: int, force_address: Optional[int] = None) -> int:
        min_overhead: Optional[int] = None
        best_chunk_idx: Optional[int] = None
        address: Optional[int] = None
        for idx, chunk in enumerate(self.free_chunks):
            if force_address is not None:
                end = force_address + size
                if force_address >= chunk.address and end <= chunk.end:
                    address = force_address
                    best_chunk_idx = idx
                    break
            elif chunk.size >= size:
                overhead = chunk.size - size
                if min_overhead is None or overhead < min_overhead:
                    min_overhead = overhead
                    best_chunk_idx = idx
                    address = chunk.address
        if best_chunk_idx is None:
            raise ValueError('Unable to allocate')
        assert address is not None

        self.free_chunks = (
            self.free_chunks[:best_chunk_idx] +
            self.free_chunks[best_chunk_idx].split(address, size) +
            self.free_chunks[best_chunk_idx+1:]
        )

        return address
