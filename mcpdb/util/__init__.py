from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Generic, Type

from ..models import *

__all__ = (
    "get_latest",
    "get_version",
    "descriptor_to_type",
    "SrgType",
    "ClassType",
    "FieldType",
    "MethodType",
    "ParamType"
)


def get_latest() -> Versions:
    return Versions.query.filter_by(latest=Active.true).one_or_none()


def get_version(version) -> Versions:
    if version == 'latest':
        return get_latest()
    return Versions.query.filter_by(version=version).one_or_none()


SIMPLE_DESC = {
    'Z': 'boolean',
    'B': 'byte',
    'C': 'char',
    'S': 'short',
    'I': 'int',
    'J': 'long',
    'F': 'float',
    'D': 'double'
}


def descriptor_to_type(desc):
    c = desc[0]
    if c == 'L':
        return desc[1:-1]
    if c == '[':
        return descriptor_to_type(desc[1:]) + '[]'
    if c in SIMPLE_DESC:
        return SIMPLE_DESC[c]
    raise ValueError("Unexpected descriptor format: " + desc)


Table = TypeVar('Table', Classes, Fields, Methods, Parameters)
History = TypeVar('History', FieldHistory, MethodHistory, ParameterHistory)


@dataclass
class SrgType(Generic[Table, History]):
    table: Type[Table]
    history: Type[History] = None


ClassType: SrgType[Classes, None] = SrgType(Classes)
FieldType: SrgType[Fields, FieldHistory] = SrgType(Fields, FieldHistory)
MethodType: SrgType[Methods, MethodHistory] = SrgType(Methods, MethodHistory)
ParamType: SrgType[Parameters, ParameterHistory] = SrgType(Parameters, ParameterHistory)
