from __future__ import annotations

from collections import Mapping
from dataclasses import dataclass
from xml.etree import ElementTree

import requests

__all__ = (
    "MavenArtifact",
    "MavenProject",
    "mcp_config",
    "mcp_stable"
)

forge_maven = 'https://files.minecraftforge.net/maven'


@dataclass
class MavenArtifact:
    project: MavenProject
    version: str
    classifier: str = None
    ext: str = "zip"

    @property
    def artifact(self):
        return "%s.%s" % ('-'.join(filter(None, [self.project.name, self.version, self.classifier])), self.ext)

    @property
    def path(self):
        return '/'.join([self.project.path, self.version, self.artifact])


@dataclass
class MavenProject:
    maven_url: str
    group: str
    name: str

    @property
    def path(self):
        return '/'.join([self.maven_url, *self.group.split('.'), self.name])

    @property
    def maven_metadata(self):
        return '/'.join([self.path, 'maven-metadata.xml'])

    def load_versions(self) -> Mapping[str, MavenArtifact]:
        with requests.get(self.maven_metadata) as resp:
            root = ElementTree.fromstring(resp.content)
            versions = root.findall(".//version")
            return {v.text: MavenArtifact(self, v.text) for v in versions}


mcp_config = MavenProject(forge_maven, 'de.oceanlabs.mcp', 'mcp_config')
mcp_stable = MavenProject(forge_maven, 'de.oceanlabs.mcp', 'mcp_stable')
