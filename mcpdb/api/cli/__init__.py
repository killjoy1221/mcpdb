import click

from .. import bp
from ... import db
from ... import util
from ...models import *
from ...tsrg import *


def check_loaded_version(version):
    if not util.get_version(version):
        raise click.ClickException("Version does not exist or is not loaded.")
    return version


@bp.cli.command()
@click.argument("version", type=util.get_version)
def promote(version: Versions):
    """Used to promote a version

    :param version: The minecraft version
    """
    if version.latest:
        raise click.ClickException("Version is already promoted")
    util.get_latest().latest = None
    version.latest = Active.true

    db.session.commit()


@bp.cli.command()
@click.argument("version", type=util.get_version)
def import_mcp(version: str):
    # TODO
    pass


@bp.cli.command()
@click.argument("version")
def import_tsrg(version):
    if util.get_version(version):
        raise click.ClickException("Version is already imported")

    if version not in util.load_mcpconfig_maven_versions():
        raise click.ClickException("No such version")

    tsrg = util.load_tsrg_mappings(version)
    import_tsrg_mappings(version, tsrg)

    click.echo("Committing to database")
    db.session.commit()

    vers = Versions(version=version)

    click.echo("Checking if it needs to be promoted")
    latest = util.get_latest()
    if latest is None:
        click.echo(f"Promoting {version} to latest.")
        vers.latest = Active.true

    db.session.add(vers)

    db.session.commit()


def import_tsrg_mappings(version, mappings: TSrg):
    click.echo(f"Loading {version} mappings with...")
    click.echo(f"\t{len(mappings.classes)} classes")
    click.echo(f"\t{len(mappings.fields)} fields")
    click.echo(f"\t{len(mappings.methods)} methods")
    click.echo(f"\t{sum(len(m.desc[0]) for m in mappings.methods.values())} parameters")

    for n, cl in enumerate(mappings.classes):
        click.echo(f"\rProcessed {n + 1}/{len(mappings.classes)} classes", nl=False)
        clas = Classes(version=version, obf_name=cl.obf.replace('/', '.'), srg_name=cl.srg.replace('/', '.'))

        for field in cl.fields.values():
            clas.fields.append(Fields(version=version, obf_name=field.obf, srg_name=field.srg, srg_id=field.srg_id))

        for method in cl.methods.values():
            desc = mappings.descriptor(method.desc)
            mtd = Methods(version=version, obf_name=method.obf, srg_name=method.srg, srg_id=method.srg_id,
                          descriptor=desc)
            clas.methods.append(mtd)

            for i, (p_type, p_name) in enumerate(zip(method.desc[0], method.params)):
                param = Parameters(version=version, obf_name='☃', srg_name=p_name, index=i,
                                   type=mappings.map_type(util.descriptor_to_type(p_type)).replace('/', '.'))
                mtd.parameters.append(param)

        db.session.add(clas)

    click.echo()
