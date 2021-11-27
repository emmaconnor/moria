from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from util import SortedList


class Type(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError('base type does not have a name')

    @property
    @abstractmethod
    def size(self) -> Optional[int]:
        raise NotImplementedError('base type does not have a size')


@dataclass
class BaseType(Type):
    _name: str
    _size: Optional[int]

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> Optional[int]:
        return self._size


@dataclass
class ArrayType(Type):
    member_type: Type
    count: int

    @property
    def name(self) -> str:
        count_repr = str(self.count) if self.count > 0 else ''
        return f'{self.member_type.name}[{count_repr}]'

    @property
    def size(self) -> Optional[int]:
        if self.member_type.size is not None:
            return self.member_type.size * self.count
        return None


@dataclass
class PointerType(Type):
    referenced_type: Type
    _size: Optional[int]

    @property
    def name(self) -> str:
        return f'{self.referenced_type.name}*'

    @property
    def size(self) -> Optional[int]:
        return self._size


@dataclass
class StructField:
    offset: int
    field_type: Type
    name: str

    def __str__(self) -> str:
        return f'0x{self.offset:04x}: {self.field_type.name} {self.name}'

    @staticmethod
    def compare_offsets(x: StructField, y: StructField) -> int:
        return x.offset - y.offset

    @property
    def size(self) -> Optional[int]:
        return self.field_type.size


class StructType(Type):
    _name: str
    fields: SortedList[StructField]

    def __init__(self, name: str) -> None:
        self._name = name
        self.fields = SortedList(key=StructField.compare_offsets)

    def add_field(self, field: StructField) -> None:
        self.fields.insert(field)

    def print_struct(self) -> None:
        print(f'{self.name} {{')
        for field in self.fields:
            print(f'  {field}')
        print(f'}} = {self.size} bytes')

    @property
    def name(self) -> str:
        return f'struct {self._name}'

    @property
    def size(self) -> Optional[int]:
        return sum(member.size for member in self.fields)
