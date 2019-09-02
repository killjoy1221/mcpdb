from __future__ import annotations

import enum
from typing import List, Union, Type

from sqlalchemy import Text, ForeignKey, Column, Integer, Boolean, Enum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy_utils import Timestamp, generic_repr, PasswordType, Password

from . import db

__all__ = (
    "Active",
    "MemberType",
    "SrgNamed",
    "McpNamed",
    "Users",
    "Versions",
    "NameHistory",
    "Classes",
    "Fields",
    "Methods",
    "Parameters",
    "SrgNamedTable",
    "McpNamedTable"
)


class Identifiable:
    id: int = Column(Integer, primary_key=True, autoincrement=True)


class Active(enum.Enum):
    true = True


class MemberType(enum.Enum):
    field = "field"
    method = "method"
    parameter = "parameter"


class SrgNamed:
    version: str = Column(Text, nullable=False)
    obf_name: str = Column(Text, nullable=False)
    srg_name: str = Column(Text, nullable=False)


class McpNamed(SrgNamed, Timestamp):
    member_type: MemberType

    locked: bool = Column(Boolean, default=False)

    @declared_attr
    def last_change_id(self) -> int:
        return Column('last_change_id', Integer, ForeignKey(NameHistory.id))

    @declared_attr
    def last_change(self) -> NameHistory:
        return relationship(NameHistory, primaryjoin=lambda: NameHistory.id == self.last_change_id)


@generic_repr
class Users(db.Model, Identifiable):
    username: str = Column(Text, nullable=False)
    password: Password = Column(PasswordType(schemes='pbkdf2_sha512'), nullable=False)
    admin: bool = Column(Boolean, default=False)


@generic_repr
class Versions(db.Model, Identifiable):
    version: str = Column(Text, nullable=False, unique=True)
    latest: bool = Column(Enum(Active), unique=True)


@generic_repr
class NameHistory(db.Model, Identifiable, Timestamp):
    member_type: MemberType = Column(Enum(MemberType), nullable=False)
    srg_name: str = Column(Text, nullable=False)
    mcp_name: str = Column(Text, nullable=False)
    changed_by_id: int = Column('changed_by_id', Integer, ForeignKey(Users.id), nullable=False)
    changed_by: Users = relationship(Users)


@generic_repr
class Classes(db.Model, Identifiable, SrgNamed):
    fields: List[Fields] = relationship("Fields", back_populates="owner")
    methods: List[Methods] = relationship("Methods", back_populates="owner")


@generic_repr
class Methods(db.Model, Identifiable, McpNamed):
    member_type = MemberType.method

    srg_id: str = Column(Integer)
    descriptor: str = Column(Text, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))

    owner: Classes = relationship("Classes", back_populates='methods')
    parameters: List[Parameters] = relationship("Parameters", back_populates='owner')


@generic_repr
class Fields(db.Model, Identifiable, McpNamed):
    member_type = MemberType.field

    srg_id: str = Column(Integer)
    class_id = Column(Integer, ForeignKey("classes.id"))
    owner = relationship("Classes", back_populates='fields')


@generic_repr
class Parameters(db.Model, Identifiable, McpNamed):
    member_type = MemberType.parameter

    index = Column(Integer, nullable=False)
    type = Column(Text, nullable=False)
    method_id = Column(Integer, ForeignKey('methods.id'), nullable=False)
    owner: Methods = relationship("Methods", back_populates='parameters')


db.Model.metadata.create_all(db.engine)

McpNamedTable = Type[Union[Methods, Fields, Parameters]]
SrgNamedTable = Type[Union[Classes, McpNamedTable]]
