from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from util import SortedList


class Type(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def size(self) -> Optional[int]:
        raise NotImplementedError


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
        count_repr = str(self.count) if self.count > 0 else ""
        return f"{self.member_type.name}[{count_repr}]"

    @property
    def size(self) -> Optional[int]:
        if self.member_type.size is not None:
            return self.member_type.size * self.count
        return None


class PointerType(Type):
    referenced_type: Type
    _size: Optional[int]

    def __init__(self, referenced_type: Type, _size: Optional[int] = 8):
        self.referenced_type = referenced_type
        self._size = _size

    @property
    def name(self) -> str:
        return f"{self.referenced_type.name}*"

    @property
    def size(self) -> Optional[int]:
        return self._size


@dataclass
class StructField:
    offset: int
    field_type: Type
    name: str

    def __repr__(self) -> str:
        return f"<StructField {self.field_type.name} {self.name}>"

    def __str__(self) -> str:
        return f"{self.field_type.name} {self.name}"

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
        print(f"{self.name} {{")
        for field in self.fields:
            print(f"  {field}")
        print(f"}} = {self.size} bytes")

    def __repr__(self) -> str:
        fields = ", ".join(str(field) for field in self.fields)
        return f"<StructType {self.name}: {fields}>"

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> Optional[int]:
        if len(self.fields) == 0:
            return None
        last_field = self.fields[len(self.fields) - 1]
        if last_field.size is None:
            return None
        return last_field.offset + last_field.size
