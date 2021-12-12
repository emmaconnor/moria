import io
import pytest

from moria.parsers.dwarf import DwarfParser

class TestDwarf:
    def test_dwarf(self) -> None:
        stream = io.BytesIO(b"definitely not a valid ELF file")
        with pytest.raises(Exception):
            DwarfParser(stream)