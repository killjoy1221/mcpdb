import io
import zipfile
from functools import lru_cache
from xml.etree import ElementTree

import requests
from flask import abort, jsonify, Response
from werkzeug.routing import BaseConverter

from . import tsrg, db
from .exc import NotFound
from .models import Versions, Classes, Methods, Fields, Parameters
from .tsrg import parse

__all__ = (
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
            clas = Classes(version=version, obf=cl.obf, name=cl.srg)
            for field in cl.fields.values():
                clas.fields.append(Fields(version=version, obf=field.obf, srg=field.srg, srg_id=field.srg_id))

            for method in cl.methods.values():
                sig = mappings.signature(method.sig)
                mtd = Methods(version=version, obf=method.obf, srg=method.srg, srg_id=method.srg_id, signature=sig)
                clas.methods.append(mtd)
                id_match = tsrg.func_regex.match(method.srg)
                if id_match:
                    srg_id = id_match.group(1)
                else:
                    srg_id = method.obf
                pargs, pret = method.sig
                for arg in range(1, len(pargs) + 1):
                    mtd.parameters.append(
                        Parameters(version=version, obf=f"p_{method.obf}_{arg}_", srg=f"p_{srg_id}_{arg}_"))

            db.session.add(clas)
        db.session.commit()


class VersionConverter(BaseConverter):
    def to_python(self, value):
        if value == 'latest':
            value = latest_version
        if value in get_versions():
            load_mappings(value)
            return value

        d, code = NotFound("No such version").response
        r: Response = jsonify(**d)
        r.status_code = code

        abort(r)
