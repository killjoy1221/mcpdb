from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, TypeVar, Generic, Type
from xml.etree import ElementTree

import requests
from flask import abort
from werkzeug.routing import BaseConverter

from . import db
from .models import *
from .tsrg import parse, func_regex

__all__ = (
    "SrgType",
    "ClassType",
    "FieldType",
    "MethodType",
    "ParamType",
    "SrgTypeConverter",
    "VersionConverter",
)

latest_version = '1.14.4'

mcp_config_url = 'https://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config'


@lru_cache()
def get_versions():
    with requests.get(f"{mcp_config_url}/maven-metadata.xml") as resp:
        root = ElementTree.fromstring(resp.content)
        versions = root.findall(".//version")
        return {v.text for v in versions if '-' not in v.text}


@lru_cache()
def get_mappings(version):
    mapped_versions = get_versions()
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


@lru_cache()
def load_mappings(version):
    if Versions.query.filter_by(version=version).one_or_none() is None:
        db.session.add(Versions(version=version))

        mappings = get_mappings(version)
        print(f"Loading {version} mappings with {len(mappings.classes)} classes")
        for cl in mappings.classes:
            clas = Classes(version=version, obf_name=cl.obf.replace('/', '.'), srg_name=cl.srg.replace('/', '.'))
            for field in cl.fields.values():
                clas.fields.append(Fields(version=version, obf_name=field.obf, srg_name=field.srg, srg_id=field.srg_id))

            for method in cl.methods.values():
                sig = mappings.signature(method.sig)
                mtd = Methods(version=version, obf_name=method.obf, srg_name=method.srg, srg_id=method.srg_id,
                              signature=sig)
                clas.methods.append(mtd)
                id_match = func_regex.match(method.srg)
                if id_match:
                    srg_id = id_match.group(1)
                else:
                    srg_id = method.obf
                pargs, pret = method.sig
                for arg in range(1, len(pargs) + 1):
                    mtd.parameters.append(
                        Parameters(version=version, obf_name=f"p_{method.obf}_{arg}_", srg_name=f"p_{srg_id}_{arg}_"))

            db.session.add(clas)
        db.session.commit()


_srg_types: Dict[str, SrgType] = {}

Table = TypeVar('Table', Classes, Fields, Methods, Parameters)
History = TypeVar('History', FieldHistory, MethodHistory, ParameterHistory)


@dataclass
class SrgType(Generic[Table, History]):
    name: str
    table: Type[Table]
    history: Type[History]

    def __str__(self):
        return self.name


def _new_srg(*args, **kwargs) -> SrgType[Table, History]:
    srg = SrgType(*args, **kwargs)
    _srg_types[srg.name] = srg
    return srg


def get_srg(name, default=None) -> SrgType[Table, History]:
    return _srg_types.get(name, default)


ClassType: SrgType[Classes, None] = _new_srg("class", Classes, None)
FieldType: SrgType[Fields, FieldHistory] = _new_srg("field", Fields, FieldHistory)
MethodType: SrgType[Methods, MethodHistory] = _new_srg("method", Methods, MethodHistory)
ParamType: SrgType[Parameters, ParameterHistory] = _new_srg("param", Parameters, ParameterHistory)


class SrgTypeConverter(BaseConverter):
    def to_python(self, value) -> SrgType:
        return get_srg(value) or abort(404)


class VersionConverter(BaseConverter):
    def to_python(self, value):
        if value == 'latest':
            value = latest_version
        if value in get_versions():
            load_mappings(value)
            return value

        abort(404)
