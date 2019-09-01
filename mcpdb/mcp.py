from csv import DictReader
from dataclasses import dataclass
from typing import List, Iterable
from zipfile import ZipFile

__all__ = (
    "McpMapping",
    "McpExport",
    "read_mcp_export"
)


@dataclass
class McpMapping:
    searge: str
    name: str
    side: str
    desc: str = None


@dataclass
class McpExport:
    fields: List[McpMapping]
    methods: List[McpMapping]
    params: List[McpMapping]


def read_mcp_export(z: ZipFile):
    fields = _read_mapping_file(z, "fields", ("searge", "name", "side", "desc"))
    methods = _read_mapping_file(z, "methods", ("searge", "name", "side", "desc"))
    params = _read_mapping_file(z, "params", ("searge", "name", "side"))
    return McpExport(fields, methods, params)


def _read_mapping_file(z: ZipFile, name: str, columns: Iterable[str]):
    f = z.read(name + ".csv").decode('utf-8').splitlines()
    reader = DictReader(f, ["searge", "name", "side", "desc"])
    return list(_read_mappings(reader))


def _read_mappings(reader: DictReader):
    for row in reader:
        yield McpMapping(*row.values())
