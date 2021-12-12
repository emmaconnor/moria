from moria.pack import FreeChunk, HeapPacker
import pytest

class TestPacker:
    def test_bad_split(self) -> None:
        with pytest.raises(ValueError):
            FreeChunk(0, 1).split(0, 2)

    def test_pack(self) -> None:
        packer = HeapPacker(0, 3)
        assert packer.alloc(1, force_address=1) == 1
        assert len(packer.free_chunks) == 2
        with pytest.raises(ValueError):
            packer.alloc(1, force_address=1)
        with pytest.raises(ValueError):
            packer.alloc(2) 

        addr1 = packer.alloc(1) 
        assert len(packer.free_chunks) == 1
        addr2 = packer.alloc(1)
        assert sorted([addr1, addr2]) == [0, 2]
        assert len(packer.free_chunks) == 0
        with pytest.raises(ValueError):
            packer.alloc(1) 

