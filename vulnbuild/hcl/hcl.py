import json
from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from dataclasses import dataclass, field, fields


@dataclass
class HclEntity(ABC):
    @abstractmethod
    def to_string(self, indent: int = 0) -> str:
        raise NotImplementedError


@dataclass
class HclConstant(HclEntity):
    name: str

    def to_string(self, indent: int = 0) -> str:
        return self.name


ValueTypes: TypeAlias = str | int | float | bool | dict | list | HclConstant


@dataclass
class HclValue(HclEntity):
    value: ValueTypes

    @classmethod
    def _serialize(cls, value: ValueTypes, indent: int = 0) -> str:
        if isinstance(value, dict):
            return '{\n' + \
                ''.join(' ' * (indent + 4) + k + ' = ' + cls._serialize(v, indent + 4) + '\n' for k, v in value.items()) + \
                (indent * ' ') + '}'
        elif isinstance(value, list):
            return '[' + ', '.join(cls._serialize(v, indent + 4) for v in value) + ']'
        elif isinstance(value, HclConstant):
            return value.to_string(indent)
        # elif isinstance(value, str):
        #     return f'"{value}"'
        else:
            return json.dumps(value)

    def to_string(self, indent: int = 0) -> str:
        return self._serialize(self.value, indent)


@dataclass
class HclArgument(HclEntity):
    name: str
    value: HclEntity

    def to_string(self, indent: int = 0) -> str:
        return f"{self.name} = {self.value.to_string(indent)}"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> list['HclArgument']:
        return [HclArgument(k, HclValue(v)) for k, v in d.items()]

    def get_raw_value(self) -> ValueTypes:
        if not isinstance(self.value, HclValue):
            raise ValueError('Not a HclValue')
        return self.value.value


@dataclass
class HclBlock(HclEntity):
    type: str
    labels: list[str] = field(default_factory=list)
    children: list[HclEntity] = field(default_factory=list)

    def to_string(self, indent: int = 0) -> str:
        prefix: str = ' ' * indent
        labels: str = "".join(" " + json.dumps(_) for _ in self.labels)
        return f'{self.type}{labels} {{\n' + \
            ''.join(prefix + '    ' + _.to_string(indent + 4) + '\n' for _ in self.children) + \
            prefix + '}\n'

    def get_argument(self, name: str) -> HclArgument | None:
        for c in self.children:
            if isinstance(c, HclArgument) and c.name == name:
                return c
        return None

    def set_argument(self, name: str, value: Any) -> None:
        if not isinstance(value, HclEntity):
            value = HclValue(value)
        arg = self.get_argument(name)
        if arg is not None:
            arg.value = value
        else:
            self.children.append(HclArgument(name, value))


@dataclass
class HclFile:
    blocks: list[HclEntity]

    def to_string(self) -> str:
        return '\n'.join(block.to_string() for block in self.blocks)

    def get_blocks(self, type: str) -> list[HclBlock]:
        return [b for b in self.blocks if isinstance(b, HclBlock) and b.type == type]

    def get_variable(self, name: str) -> HclBlock | None:
        for block in self.get_blocks('variable'):
            if block.labels[0] == name:
                return block
        return None

    def add_variable(self, var: HclBlock) -> None:
        for i, b in enumerate(self.blocks):
            if isinstance(b, HclBlock) and b.type == 'source':
                self.blocks = self.blocks[:i] + [var] + self.blocks[i:]
                return
        self.blocks.append(var)

    def clone(self) -> 'HclFile':
        from vulnbuild.hcl.parser import HclParser
        return HclParser.parse(self.to_string())
