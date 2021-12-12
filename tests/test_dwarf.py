from __future__ import annotations
from dataclasses import dataclass
import io
import json
from typing import BinaryIO, Iterable, List, Optional, Union

import pytest
from pytest_mock import MockerFixture
from moria.arch import Endianness
from moria.basetypes import IntType, PointerType, StructType

from moria.parsers.dwarf import DW_ATE_address, DW_ATE_signed, DW_ATE_signed_char, DW_ATE_unsigned, DwarfParser
from moria.values import StructValue


@dataclass
class MockDIEAttribute:
    value: Union[int, bytes]
    die_ref_name: Optional[str] = None
    die_ref: Optional[MockDIE] = None


class MockDIE:
    name: Optional[str]
    tag: str
    attributes: dict[str, MockDIEAttribute]
    children: List[MockDIE]

    def __init__(self,
                 tag: str,
                 attributes: dict[str, MockDIEAttribute],
                 children: Iterable[MockDIE],
                 name: Optional[str] = None) -> None:
        self.tag = tag
        self.attributes = attributes
        self.children = list(children)
        self.name = name

    def iter_children(self) -> Iterable[MockDIE]:
        return self.children

    def get_DIE_from_attribute(self, attribute_name: str) -> MockDIE:
        die = self.attributes[attribute_name].die_ref
        assert die is not None
        return die


class MockCompilationUnit:
    top_die: MockDIE
    dies_by_name: dict[str, MockDIE]
    all_dies: List[MockDIE]

    def __init__(self, json_data: dict) -> None:
        die_data = json_data['die']
        self.all_dies = []
        self.dies_by_name = {}
        self.top_die = self.parse_die(die_data)
        self.resolve_die_refs()

    def resolve_die_refs(self):
        for die in self.all_dies:
            for attribute in die.attributes.values():
                if attribute.die_ref_name is not None:
                    attribute.die_ref = self.dies_by_name[attribute.die_ref_name]

    def parse_die(self, die_data: dict) -> MockDIE:
        children_data = die_data.get('children')
        children = []
        if children_data is not None:
            children = [self.parse_die(child_data) for child_data in children_data]

        attributes = {}
        attributes_data = die_data.get('attributes')
        if attributes_data is not None:
            for attribute_data in attributes_data:
                name = attribute_data['name']
                value = attribute_data.get('value')
                if isinstance(value, str):
                    value = value.encode('utf=8')
                attributes[name] = MockDIEAttribute(
                    value, die_ref_name=attribute_data.get('die_ref'))

        die_name = die_data.get('name')
        die = MockDIE(die_data['tag'], attributes, children, die_name)
        self.all_dies.append(die)
        if die_name is not None:
            self.dies_by_name[die_name] = die
        return die

    def get_top_DIE(self) -> MockDIE:
        return self.top_die


class MockDwarfInfo:
    compilation_units: List[MockCompilationUnit]

    def __init__(self, json_data: dict) -> None:
        self.compilation_units = [MockCompilationUnit(
            cu_data) for cu_data in json_data['compilation_units']]

    def iter_CUs(self) -> Iterable[MockCompilationUnit]:
        return self.compilation_units


class MockELFFile:
    elfclass: int
    little_endian: bool
    dwarf_info: Optional[MockDwarfInfo]

    def __init__(self, stream: BinaryIO) -> None:
        json_data = json.load(stream)
        self.elfclass = json_data['elfclass']
        self.little_endian = json_data['little_endian']
        dwarf_info_data = json_data.get('dwarf_info')
        self.dwarf_info = MockDwarfInfo(
            dwarf_info_data) if dwarf_info_data is not None else None

    def has_dwarf_info(self) -> bool:
        return self.dwarf_info is not None

    def get_dwarf_info(self) -> MockDwarfInfo:
        assert self.dwarf_info is not None
        return self.dwarf_info


int_die = {
    'name': 'int',
    'tag': 'DW_TAG_base_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'int',
        },
        {
            'name': 'DW_AT_byte_size',
            'value': 4,
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_signed,
        },
    ],
}

void_ptr_die = {
    'name': 'void',
    'tag': 'DW_TAG_pointer_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'void',
        },
        {
            'name': 'DW_AT_byte_size',
            'value': 8,
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_address,
        },
    ],
}

char_die = {
    'name': 'char',
    'tag': 'DW_TAG_base_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'char',
        },
        {
            'name': 'DW_AT_byte_size',
            'value': 1,
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_signed_char,
        },
    ],
}

uint64_die = {
    'name': 'uint64_t',
    'tag': 'DW_TAG_base_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'uint64_t',
        },
        {
            'name': 'DW_AT_byte_size',
            'value': 8,
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_unsigned,
        },
    ],
}

typedef_int_num_die = {
    'name': 'num',
    'tag': 'DW_TAG_typedef',
    'attributes': [
        {
            'name': 'DW_AT_type',
            'die_ref': 'int',
        },
    ],
}

typedef_partial_die = {
    'name': 'partial_t',
    'tag': 'DW_TAG_typedef',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'partial_t',
        },
    ],
}

partial_ptr_die = {
    'name': 'partial_ptr',
    'tag': 'DW_TAG_pointer_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'void',
        },
        {
            'name': 'DW_AT_type',
            'die_ref': 'partial_t',
        },
        {
            'name': 'DW_AT_byte_size',
            'value': 8,
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_address,
        },
    ],

}

char_array_die = {
    'name': 'char_array',
    'tag': 'DW_TAG_array_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'char[16]',
        },
        {
            'name': 'DW_AT_type',
            'die_ref': 'char',
        },
        {
            'name': 'DW_AT_encoding',
            'value': DW_ATE_address,
        },
    ],
    'children': [
        {
            'tag': 'DW_TAG_subrange_type',
            'attributes': [
                {
                    'name': 'DW_AT_upper_bound',
                    'value': 15,
                },
            ]
        }
    ],
}

child_struct_die = {
    'name': 'child_struct',
    'tag': 'DW_TAG_structure_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'child_struct',
        },
    ],
    'children': [
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'child_uint64_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'uint64_t',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 0,
                },
            ],
        },
    ],
}

struct_die = {
    'tag': 'DW_TAG_structure_type',
    'attributes': [
        {
            'name': 'DW_AT_name',
            'value': 'test',
        },
    ],
    'children': [
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'int_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'int',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 0,
                },
            ],
        },
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'void_ptr_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'void',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 8,
                },
            ],
        },
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'char_arr_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'char_array',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 16,
                },
            ],
        },
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'nested_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'child_struct',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 32,
                },
            ],
        },
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'num_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'num',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 40,
                },
            ],
        },
        {
            'tag': 'DW_TAG_member',
            'attributes': [
                {
                    'name': 'DW_AT_name',
                    'value': 'partial_ptr_field',
                },
                {
                    'name': 'DW_AT_type',
                    'die_ref': 'partial_ptr',
                },
                {
                    'name': 'DW_AT_data_member_location',
                    'value': 44,
                },
            ],
        },
    ],
}

elf_data_amd64 = {
    'elfclass': 64,
    'little_endian': True,
    'dwarf_info': {
        'compilation_units': [
            {
                'die': {
                    'tag': 'DW_TAG_compile_unit',
                    'children': [
                        typedef_int_num_die,
                        typedef_partial_die,
                        partial_ptr_die,
                        uint64_die,
                        char_die,
                        char_array_die,
                        int_die,
                        struct_die,
                        void_ptr_die,
                        child_struct_die,
                    ]
                }
            }
        ]
    }
}


class TestDwarf:
    def test_unsupported_tag(self, mocker: MockerFixture) -> None:
        mocker.patch('moria.parsers.dwarf.ELFFile', new=MockELFFile)
        deep_elf_copy = json.loads(json.dumps(elf_data_amd64))
        uint64_die = deep_elf_copy['dwarf_info']['compilation_units'][0]['die']['children'][3]
        uint64_die['tag'] = 'asdf'

        stream = io.BytesIO(json.dumps(deep_elf_copy).encode('utf-8'))
        with pytest.raises(NotImplementedError):
            DwarfParser(stream).create_namespace()

    def test_unsupported_encoding(self, mocker: MockerFixture) -> None:
        mocker.patch('moria.parsers.dwarf.ELFFile', new=MockELFFile)
        deep_elf_copy = json.loads(json.dumps(elf_data_amd64))
        uint64_die = deep_elf_copy['dwarf_info']['compilation_units'][0]['die']['children'][3]
        uint64_die['attributes'][2]['value'] = 0x1337

        stream = io.BytesIO(json.dumps(deep_elf_copy).encode('utf-8'))
        with pytest.raises(NotImplementedError):
            DwarfParser(stream).create_namespace()

    def test_unsupported_class(self, mocker: MockerFixture) -> None:
        mocker.patch('moria.parsers.dwarf.ELFFile', new=MockELFFile)
        bad_elf = {
            'elfclass': 63,
            'little_endian': True,
            'dwarf_info': {
                'compilation_units': []
            }
        }
        stream = io.BytesIO(json.dumps(bad_elf).encode('utf-8'))
        with pytest.raises(NotImplementedError):
            DwarfParser(stream).create_namespace()

    def test_no_dwarf(self, mocker: MockerFixture) -> None:
        mocker.patch('moria.parsers.dwarf.ELFFile', new=MockELFFile)
        bad_elf = {
            'elfclass': 64,
            'little_endian': True,
        }
        stream = io.BytesIO(json.dumps(bad_elf).encode('utf-8'))
        with pytest.raises(ValueError):
            DwarfParser(stream).create_namespace()

    def test_dwarf(self, mocker: MockerFixture, capfd: pytest.CaptureFixture) -> None:
        mocker.patch('moria.parsers.dwarf.ELFFile', new=MockELFFile)
        stream = io.BytesIO(json.dumps(elf_data_amd64).encode('utf-8'))
        ns = DwarfParser(stream).create_namespace()
        assert ns.arch.pointer_size == 8
        assert ns.arch.endianness == Endianness.LITTLE
        assert issubclass(ns.test, StructValue)
        assert isinstance(ns.test.type, StructType)
        assert len(ns.test.type.fields) == 6

        assert ns.test.type.fields[0].name == 'int_field'
        assert ns.test.type.fields[0].field_type == ns.Int.type

        assert ns.test.type.fields[1].name == 'void_ptr_field'
        assert ns.test.type.fields[1].field_type == ns.VoidPointer.type

        assert ns.test.type.fields[2].name == 'char_arr_field'
        assert ns.test.type.fields[2].field_type == ns.array(ns.Char, 16).type

        assert ns.test.type.fields[3].name == 'nested_field'
        assert ns.test.type.fields[3].field_type == ns.child_struct.type

        assert ns.test.type.fields[4].name == 'num_field'
        assert isinstance(ns.test.type.fields[4].field_type, IntType)
        assert ns.test.type.fields[4].field_type.signed == True
        assert ns.test.type.fields[4].field_type.size == 4

        assert ns.test.type.fields[5].name == 'partial_ptr_field'
        assert isinstance(ns.test.type.fields[5].field_type, PointerType)
        assert isinstance(ns.test.type.fields[5].field_type.referenced_type, IntType)
        assert ns.test.type.fields[5].field_type.referenced_type.size is None

        ns.print_structs()
        out, err = capfd.readouterr()
        assert err == ''
        assert out == '''
struct test {
  int int_field;
  void* void_ptr_field;
  char[16] char_arr_field;
  struct child_struct {
    uint64_t child_uint64_field;
  };
  int num_field;
  partial_t* partial_ptr_field;
};

struct child_struct {
  uint64_t child_uint64_field;
};
'''[1:]

    def test_invalid(self) -> None:
        stream = io.BytesIO(b"definitely not a valid ELF file")
        with pytest.raises(Exception):
            DwarfParser(stream)
