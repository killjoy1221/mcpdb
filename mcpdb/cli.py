import click

from . import app, db, util
from .models import *
from .util import mcp, tsrg, maven

__all__ = ()


def check_loaded_version(version):
    if not util.get_version(version):
        raise click.ClickException("Version does not exist or is not loaded.")
    return version


@app.cli.command()
@click.argument("statement")
def execute(statement):
    for s in db.engine.execute(statement):
        click.echo(s)


@app.cli.command()
@click.argument("username")
@click.password_option('--password')
def adduser(username, password):
    user = Users(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    click.echo("User created.")


@app.cli.command()
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


@app.cli.command()
@click.argument("version", type=str)
@click.option("--target", type=util.get_version, default="latest")
def import_mcp(version: str, target: Versions):
    # Import as the first user (admin)
    user: Users = Users.query.first()
    if user is None:
        raise click.ClickException("No users created. "
                                   "Create a user using the 'flask adduser' command to add an admin user.")

    if target is None:
        raise click.ClickException("No such version. You may need to import it using 'flask import-tsrg'")

    versions = maven.mcp_stable.load_versions()
    if version not in versions:
        raise click.ClickException("mcp_stable version does not exist.")

    artifact = versions[version]
    click.echo(f"Will import '{artifact.artifact}' into '{target.version}' as user '{user.username}'.")
    click.confirm("Confirm?")

    click.echo(f"Fetching mcp_stable {artifact.artifact}")
    mappings = mcp.load_mcp_mappings(artifact)
    import_mcp_mappings(user, target.version, mappings)

    click.echo("Committing... ", nl=False)
    db.session.commit()
    click.echo("Done")


def import_mcp_mappings(user: Users, version: str, mappings: mcp.McpExport):
    def process(m, srg_type: util.SrgType):
        name = srg_type.table.__tablename__
        entries = {e.srg_name: e for e in srg_type.table.query.filter_by(version=version)}
        for i, e in enumerate(m):
            click.echo(f"\rProcessing {i + 1}/{len(m) + 1} {name}... ", nl=False)
            if e.searge in entries:
                info = entries[e.searge]
                if info.last_change is None:
                    info.last_change = srg_type.history(
                        srg_name=e.searge,
                        mcp_name=e.name,
                        changed_by=user
                    )
        click.echo("Done")

    fields = mappings.fields, util.FieldType
    methods = mappings.methods, util.MethodType
    params = mappings.params, util.ParamType

    for f, t in fields, methods, params:
        process(f, t)


@app.cli.command()
@click.argument("target", type=util.get_version)
@click.option("--origin", type=util.get_version, default='latest')
def migrate_mcp(target: Versions, origin: Versions):
    migrate_mcp_mappings(origin.version, target.version)


def migrate_mcp_mappings(mcp_from, mcp_to):
    def migrate(table):
        name = table.__tablename__
        old_entries = {e.srg_name: e for e in table.query.filter_by(version=mcp_from)}
        new_entries = table.query.filter_by(version=mcp_to).all()
        for i, entry in enumerate(new_entries):
            click.echo(f"\rProcessed {i + 1}/{len(new_entries) + 1} {name}... ", nl=False)
            if entry.srg_name in old_entries and entry.last_change is None:
                entry.last_change = old_entries[entry.srg_name].last_change
        click.echo("Done")
        db.session.commit()

    for t in Fields, Methods, Parameters:
        # noinspection PyTypeChecker
        migrate(t)


@app.cli.command()
@click.argument("version")
def import_tsrg(version):
    if util.get_version(version):
        raise click.ClickException("Version is already imported")

    versions = maven.mcp_config.load_versions()
    if version not in versions:
        raise click.ClickException("No such version")

    artifact = versions[version]

    click.echo(f"Fetching {artifact.artifact}")
    srg = tsrg.load_tsrg_mappings(artifact)

    import_tsrg_mappings(version, srg)

    click.echo("Committing to database...", nl=False)
    db.session.commit()
    click.echo(" Done")
    vers = Versions(version=version)

    click.echo("Checking if it needs to be promoted...")
    latest = util.get_latest()
    if latest is None:
        click.echo(f"Promoting {version} to latest.")
        vers.latest = Active.true
    else:
        click.echo("Nope.")

    db.session.add(vers)
    db.session.commit()


def import_tsrg_mappings(version, mappings: tsrg.TSrg):
    click.echo(f"Loading {version} mappings with...")
    click.echo(f"\t{len(mappings.classes)} classes")
    click.echo(f"\t{len(mappings.fields)} fields")
    click.echo(f"\t{len(mappings.methods)} methods")
    click.echo(f"\t{sum(len(m.desc[0]) for m in mappings.methods.values())} parameters")

    for n, cl in enumerate(mappings.classes):
        click.echo(f"\rProcessed {n + 1}/{len(mappings.classes)} classes", nl=False)
        clas = Classes(version=version, obf_name=cl.obf.replace('/', '.'), srg_name=cl.srg.replace('/', '.'))

        for field in cl.fields.values():
            sid = field.srg_id
            clas.fields.append(
                Fields(version=version, obf_name=field.obf, srg_name=field.srg, srg_id=sid, locked=sid is None))

        for method in cl.methods.values():
            desc = mappings.descriptor(method.desc)
            sid = method.srg_id
            mtd = Methods(version=version, obf_name=method.obf, srg_name=method.srg, srg_id=sid,
                          locked=sid is None, descriptor=desc)
            clas.methods.append(mtd)

            for i, (p_type, p_name) in enumerate(zip(method.desc[0], method.params)):
                param = Parameters(version=version, obf_name='☃', srg_name=p_name, index=i,
                                   type=mappings.map_type(util.descriptor_to_type(p_type)).replace('/', '.'))
                mtd.parameters.append(param)

        db.session.add(clas)

    click.echo()
