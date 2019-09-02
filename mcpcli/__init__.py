"""
quick cli for testing the api
"""

import click
import requests

url = 'http://localhost:5000/api'


@click.group()
def cli():
    pass


@cli.command()
@click.argument('srg')
@click.option('--version', default='latest', type=str)
def gf(srg, version):
    with requests.get(f'{url}/field/{srg}?version={version}') as resp:
        click.echo(resp.json())


@cli.command()
@click.argument('srg')
@click.argument('name')
@click.option('--version', default='latest', type=str)
@click.option('--force', '-f', is_flag=True)
def sf(srg, name, version, force):
    data = {
        'mcpname': name,
        'force': force
    }
    with requests.put(f'{url}/field/{srg}?version={version}', json=data) as resp:
        click.echo(resp.json())


@cli.command()
@click.argument('srg')
def fh(srg, *, version='latest'):
    with requests.get(f'{url}/field/{srg}/history') as resp:
        click.echo(resp.json())
