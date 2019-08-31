from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import TypeVar, Generic, Type
from xml.etree import ElementTree

import requests

from .models import *
from .tsrg import parse

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


mcp_config_url = 'https://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config'


def load_mcpconfig_maven_versions():
    with requests.get(f"{mcp_config_url}/maven-metadata.xml") as resp:
        root = ElementTree.fromstring(resp.content)
        versions = root.findall(".//version")
        return {v.text for v in versions if '-' not in v.text}


def load_tsrg_mappings(version):
    mapped_versions = load_mcpconfig_maven_versions()
    if version not in mapped_versions:
        raise ValueError()

    print(f"Fetching mcp_config-{version}.zip")
    with requests.get(f"{mcp_config_url}/{version}/mcp_config-{version}.zip") as resp:
        zipbytes = io.BytesIO(resp.content)

        with zipfile.ZipFile(zipbytes, 'r') as z:
            joined = z.read('config/joined.tsrg').decode('utf-8').splitlines()
            ts = parse(joined)

            static_methods = z.read('config/static_methods.txt').decode('utf-8').splitlines()
            for func in static_methods:
                ts.methods[func].static = True

            constructors = z.read('config/constructors.txt').decode('utf-8').splitlines()
            for c in constructors:
                c_id, owner, sig = c.split(' ')
                if owner in ts.classes.by_srg:
                    ts.classes.by_srg[owner].add_constructor(*c.split(' '))

            return ts


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
