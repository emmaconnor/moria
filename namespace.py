from typing import MutableMapping

from basetypes import StructType


class Namespace:
    def __init__(self) -> None:
        self.structs: MutableMapping[str, StructType] = {}

    def get_or_create(self, name: str) -> StructType:
        struct = self.structs.get(name)
        if struct is not None:
            return struct
        struct = StructType(name)
        self.structs[name] = struct
        return struct

    def print_structs(self):
        for i, struct in enumerate(self.structs.values()):
            if i > 0:
                print()
            struct.print_struct()
