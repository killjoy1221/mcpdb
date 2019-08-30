from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, TypeVar, Generic, Optional, Iterable, List, Tuple

field_regex = re.compile(r'^field_(\d+)_(\w+)$')
func_regex = re.compile(r'^func_(\d+)_(\w+)$')
param_regex = re.compile(r'^p_(\d+)_(\d+)_$')


@dataclass
class SrgMapping:
    obf: str
    srg: str


T = TypeVar('T', bound=SrgMapping)


class SrgContainer(Generic[T], Iterable[T]):
    def __init__(self):
        self.by_srg: Dict[str, T] = {}
        self.by_obf: Dict[str, T] = {}

    def add(self, mapping: T):
        self.by_srg[mapping.srg] = mapping
        self.by_obf[mapping.obf] = mapping

    def map(self, unmapped):
        c = self.by_obf.get(unmapped)
        if c is None:
            return unmapped
        return c.srg

    def unmap(self, mapped):
        c = self.by_srg.get(mapped)
        if c is None:
            return mapped
        return c.obf

    def __iter__(self):
        return iter(self.by_srg.values())

    def __len__(self):
        return len(self.by_srg)


class TSrg:
    def __init__(self):
        self.classes: SrgContainer[TClass] = SrgContainer()
        self.fields: Dict[str, TField] = {}
        self.methods: Dict[str, TMethod] = {}

    def signature(self, sig: Tuple[List[str], str]):
        args, ret = sig

        def map_param(name):
            if name[0] == 'L':
                return f"L{self.classes.map(name[1:-1])};"
            return name

        return f"({''.join(map_param(p) for p in args)}){map_param(ret)}"


@dataclass
class TClass(SrgMapping):
    fields: Dict[str, TField] = field(default_factory=dict)
    constructors: Dict[int, TConstructor] = field(default_factory=dict)
    methods: Dict[str, TMethod] = field(default_factory=dict)

    def add_constructor(self, c_id, owner, signature):
        self.constructors[c_id] = TConstructor(c_id, owner, parse_descriptor(signature))


@dataclass
class TField(SrgMapping):
    owner: TClass

    @property
    def srg_id(self):
        m = field_regex.match(self.srg)
        return m.group(1) if m else self.srg


@dataclass
class TConstructor:
    srg_id: int
    owner: TClass
    sig: Tuple[List[str], str]


@dataclass
class TMethod(SrgMapping):
    sig: Tuple[List[str], str]
    owner: TClass
    static: bool = False

    @property
    def srg_id(self):
        m = func_regex.match(self.srg)
        return m.group(1) if m else self.srg

    @property
    def obf_params(self):
        start = 0 if self.static else 1
        end = start + len(self.sig[0])
        return [f'p_{self.obf}_{n}_' for n in range(start, end)]

    @property
    def srg_params(self):
        start = 0 if self.static else 1
        end = start + len(self.sig[0])
        return [f'p_{self.srg_id}_{n}_' for n in range(start, end)]


def parse(tsrg_stream: Iterable[str]) -> TSrg:
    tsrg = TSrg()
    current_class: Optional[TClass] = None
    for line in tsrg_stream:
        if not line.startswith('\t'):
            # Classes
            obf, srg = line.split(' ')
            current_class = TClass(obf, srg)
            tsrg.classes.add(current_class)
        elif '(' in line:
            # Methods
            obf, sig, srg = line.strip().split(' ')
            m = TMethod(obf, srg, parse_descriptor(sig), current_class)
            current_class.methods[srg] = m
            tsrg.methods[srg] = m
        else:
            # Fields
            obf, srg = line.strip().split(' ')
            f = TField(obf, srg, current_class)
            current_class.fields[srg] = f
            tsrg.fields[srg] = f

    return tsrg


def parse_descriptor(signature) -> Tuple[List[str], str]:
    args, ret = re.match(r'\((.*)\)(.*)', signature).groups()
    targs = []
    array = 0
    current_type: Optional[List[str]] = None
    for c in args:
        if current_type is None and c == '[':
            array += 1
        elif current_type is None:
            if c == 'L':
                current_type = [c]
            else:
                if array:
                    c = '[' * array + c
                    array = 0
                targs.append(c)
        else:
            current_type.append(c)
            if c == ';':
                joined = ''.join(current_type)
                if array:
                    joined = '[' * array + joined
                    array = 0
                targs.append(joined)
                current_type = None

    return targs, ret