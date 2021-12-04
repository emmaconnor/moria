from typing import Iterable, BinaryIO

from elftools.elf.elffile import ELFFile
from elftools.dwarf.die import DIE
from arch import Arch, Endianness

from basetypes import (
    IntType,
    PointerType,
    ArrayType,
    StructField,
    Type,
)
import namespace


class DwarfParser:
    def __init__(self, stream: BinaryIO) -> None:
        self.elf_file = ELFFile(stream)

        if self.elf_file.elfclass in (32, 64):
            word_size = self.elf_file.elfclass // 8
        else:
            raise NotImplementedError(
                f"Unsupported elf class: {self.elf_file.elfclass}"
            )

        endianness = (
            Endianness.LITTLE
            if self.elf_file.little_endian
            else Endianness.BIG
        )

        if not self.elf_file.has_dwarf_info():
            raise ValueError("File has no DWARf debug info.")
            return

        self.dwarf_info = self.elf_file.get_dwarf_info()
        self.namespace = namespace.Namespace(Arch(endianness, word_size))

    def create_namespace(self) -> namespace.Namespace:
        for compilation_unit in self.dwarf_info.iter_CUs():
            top_DIE = compilation_unit.get_top_DIE()
            self.recurse_die(top_DIE)
        self.namespace.initialize_struct_classes()
        return self.namespace

    def recurse_die(self, die: DIE) -> None:
        if die.tag == "DW_TAG_structure_type":
            self.process_struct_die(die)

        for child in die.iter_children():
            self.recurse_die(child)

    def process_struct_die(self, die: DIE) -> None:
        struct_name = die.attributes["DW_AT_name"].value.decode("utf-8")
        struct = self.namespace.get_or_create_struct_type(struct_name)
        for child in die.iter_children():
            assert child.tag == "DW_TAG_member"

            member_name = child.attributes["DW_AT_name"].value.decode("utf-8")
            member_type = self.resolve_type(child)
            member_offset = child.attributes[
                "DW_AT_data_member_location"
            ].value
            struct.add_field(
                StructField(
                    self.namespace, member_offset, member_type, member_name
                )
            )

    def resolve_type(self, die: DIE) -> Type:
        if (
            die.tag == "DW_TAG_pointer_type"
            and "DW_AT_type" not in die.attributes
        ):
            type_size = die.attributes.get("DW_AT_byte_size").value
            return PointerType(
                IntType(self.namespace, "void", None), type_size
            )

        type_die = die.get_DIE_from_attribute("DW_AT_type")
        if type_die.tag == "DW_TAG_pointer_type":
            pointed_type = self.resolve_type(type_die)
            type_size = type_die.attributes.get("DW_AT_byte_size").value
            return PointerType(pointed_type, type_size)
        elif type_die.tag == "DW_TAG_array_type":
            counts = self.get_array_counts(type_die)
            elem_type = self.resolve_type(type_die)
            array_type = elem_type
            for count in counts:
                array_type = ArrayType(self.namespace, array_type, count)
            return array_type
        elif type_die.tag == "DW_TAG_structure_type":
            type_name = type_die.attributes.get("DW_AT_name").value.decode(
                "utf-8"
            )
            return self.namespace.get_or_create_struct_type(type_name)
        elif type_die.tag == "DW_TAG_base_type":
            type_name = type_die.attributes.get("DW_AT_name").value.decode(
                "utf-8"
            )
            type_size = type_die.attributes.get("DW_AT_byte_size").value
            return IntType(self.namespace, type_name, type_size)
        elif type_die.tag == "DW_TAG_typedef":
            if "DW_AT_type" in type_die.attributes:
                return self.resolve_type(type_die)
            type_name = type_die.attributes.get("DW_AT_name").value.decode(
                "utf-8"
            )
            type_size = type_die.attributes.get("DW_AT_byte_size")
            return IntType(
                self.namespace,
                type_name,
                type_size.value if type_size is not None else None,
            )
        else:
            raise NotImplementedError(f"Unknown type tag: {type_die.tag}")

    def get_array_counts(self, die: DIE) -> Iterable[int]:
        counts = []
        for child in die.iter_children():
            if child.tag == "DW_TAG_subrange_type":
                count = child.attributes["DW_AT_upper_bound"].value + 1
                counts.append(count)
        return counts
