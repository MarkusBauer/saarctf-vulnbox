import json
from typing import Any, Iterable, TypeVar

import hcl2

from vulnbuild.hcl.hcl import HclFile, HclEntity, HclBlock, HclValue, HclArgument, HclConstant

_T = TypeVar('_T')


def concat_lists(lsts: Iterable[list[_T]]) -> list[_T]:
    result = []
    for lst in lsts:
        result += lst
    return result


class HclParser:
    block_types: dict[str, int] = {
        'provisioner': 1,
        'required_plugins': 0,
        'vulnbuild': 1,
    }

    top_level_block_types: dict[str, int] = {
        'build': 0,
        'packer': 0,
        'source': 2,
        'variable': 1,
    }

    @classmethod
    def _parse_value(cls, value: Any) -> HclValue:
        value = cls._parse_constants(value)
        return HclValue(value)

    @classmethod
    def _parse_constants(cls, value: Any) -> Any:
        match value:
            case dict() as d:
                return {k: cls._parse_constants(v) for k, v in d.items()}  # type: ignore
            case list() as l:
                return [cls._parse_constants(v) for v in l]  # type: ignore
            case '${string}' | '${number}' | '${boolean}' as s:
                return HclConstant(s[2:-1])
            case str() as s:
                return json.loads(f'"{s}"')
            case _:
                return value

    @classmethod
    def _parse_blocks(cls, type: str, labels: list[str], remaining_labels: int, value: Any) -> list[HclEntity]:
        if remaining_labels > 0:
            if isinstance(value, dict) and len(value) == 1:
                label, value = list(value.items())[0]
                return cls._parse_blocks(type, labels + [label], remaining_labels - 1, value)
            if isinstance(value, list):
                return concat_lists(cls._parse_blocks(type, labels, remaining_labels, x) for x in value)
        return [HclBlock(type=type, labels=labels, children=cls._parse_collection(value))]

    @classmethod
    def _parse_dict_item(cls, key: str, value: Any, top_level: bool = False) -> list[HclEntity]:
        if top_level and key in cls.top_level_block_types:
            return cls._parse_blocks(key, [], cls.top_level_block_types[key], value)
        if key in cls.block_types:
            return cls._parse_blocks(key, [], cls.block_types[key], value)
        return [HclArgument(key, cls._parse_value(value))]

    @classmethod
    def _parse_collection(cls, value: Any, top_level: bool = False) -> list[HclEntity]:
        if isinstance(value, list):
            return concat_lists(cls._parse_collection(x) for x in value)
        elif isinstance(value, dict):
            return concat_lists(cls._parse_dict_item(key, val, top_level=top_level) for key, val in value.items())
        else:
            raise ValueError(f"Unsupported type {type(value)}")

    @classmethod
    def parse(cls, text: str) -> HclFile:
        d = hcl2.loads(text)
        return HclFile(cls._parse_collection(d, top_level=True))
