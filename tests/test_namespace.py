import pytest
from tests.helpers import amd64_namespace
from moria.basetypes import Type
from typing import Any


class TestNamespace:
    def test_no_superclass(self) -> None:
        ns = amd64_namespace()

        with pytest.raises(TypeError):
            ns._get_superclass_for_type(None) # type: ignore

    def test_conflicting_struct_name(self) -> None:
        ns = amd64_namespace()
        ns.get_or_create_struct_type('__init__')
        with pytest.raises(ValueError):
            ns.initialize_struct_classes()

    def test_struct_name(self) -> None:
        ns = amd64_namespace()
        assert ns._format_struct_name('test') == 'test'
        with pytest.raises(ValueError):
            ns._format_struct_name('!')

    def test_pack_cyclic(self) -> None:
        ns = amd64_namespace()
        i = ns.Int()
        j = ns.Int()

        # Cyclic address dependencies are not supported, even when consistent.
        i.address_base = j
        i.offset = -4
        j.address_base = i
        j.offset = 4

        with pytest.raises(ValueError):
            ns.pack_values(0x0, 0x100, [i])

    def test_pack_implicit(self) -> None:
        ns = amd64_namespace()
        char_arr = ns.array(ns.Char, 4)
        test_char_arr = char_arr.cast("test")
        test_ptr = test_char_arr.values[0].ref()
        packed_vals = ns.pack_values(0x0, 12, [test_ptr])

        # The allocator may choose any order to pack the values, so
        # there are two possible valid packings that are OK to return.
        assert packed_vals in (
            b'test\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\x08\x00\x00\x00\x00\x00\x00\x00test',
        )

    def test_pack(self) -> None:
        ns = amd64_namespace()
        assert ns.pack_values(0x0, 0x1000, []) == b''

        i = ns.UInt32(0xdeadbeef)
        assert ns.pack_values(0x0, 0x1000, [i]) == b'\xef\xbe\xad\xde'

        i_ptr = i.ref()
        packed_vals = ns.pack_values(0x0, 12, [i, i_ptr])

        # The allocator may choose any order to pack the values, so
        # there are two possible valid packings that are OK to return.
        assert packed_vals in (
            b'\xef\xbe\xad\xde\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\x08\x00\x00\x00\x00\x00\x00\x00\xef\xbe\xad\xde',
        )

        # This is invalid because there is not enough space
        with pytest.raises(ValueError):
            ns.pack_values(0x0, 11, [i, i_ptr])

        # This is invalid because the objects already have fixed
        # addresses incompatible with the given address range.
        with pytest.raises(ValueError):
            ns.pack_values(0x10, 12, [i, i_ptr])
