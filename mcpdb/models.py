from __future__ import annotations

from typing import Type, List

from sqlalchemy import Text, ForeignKey, Column, Integer, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy_utils import Timestamp, generic_repr

from . import db

__all__ = (
    "Users",
    "UserPermissions",
    "Tokens",
    "TokenPermissions",
    "Versions",
    "Classes",
    "FieldHistory",
    "Fields",
    "MethodHistory",
    "Methods",
    "ParameterHistory",
    "Parameters"
)


@generic_repr
class Users(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    github_token: str = Column(Text, nullable=False)
    name: str = Column(Text, nullable=False)

    permissions: List[UserPermissions]
    tokens: List[Tokens]


@generic_repr
class UserPermissions(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey(Users.id), nullable=False)
    name: str = Column(Text, nullable=False)


@generic_repr
class Tokens(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey(Users.id), nullable=False)
    description: str = Column(Text, nullable=False)
    token: str = Column(Text, nullable=False, unique=True)

    user: Users = relationship(Users)
    permissions: List[TokenPermissions]


@generic_repr
class TokenPermissions(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    token_id: int = Column(Integer, ForeignKey(Tokens.id), nullable=False)
    name: str = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint(token_id, name),
    )


Users.permissions = relationship(UserPermissions)
Users.tokens = relationship(Tokens)
Tokens.permissions = relationship(TokenPermissions)


@generic_repr
class Versions(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    version: str = Column(Text, nullable=False, unique=True)


@generic_repr
class Classes(db.Model):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    version: str = Column(Text, nullable=False)
    obf: str = Column(Text, nullable=False)
    name: str = Column(Text, nullable=False)

    fields: List[Fields] = relationship("Fields", back_populates="clas")
    methods: List[Methods] = relationship("Methods", back_populates="clas")

    def to_json(self):
        return dict(
            version=self.version,
            obf=self.obf,
            name=self.name
        )


class _SrgHistory(Timestamp):
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    version: str = Column(Text, nullable=False)
    srg: str = Column(Text, nullable=False)
    name: str = Column(Text, nullable=False)

    @declared_attr
    def changed_by_id(self) -> int:
        return Column('changed_by_id', Integer, ForeignKey(Users.id), nullable=False)

    @declared_attr
    def changed_by(self) -> Users:
        return relationship(Users)

    def to_json(self):
        return dict(
            version=self.version,
            srg=self.srg,
            name=self.name,
            changed_by=self.changed_by.name,
            created=self.created
        )


def _SrgNamed(history_table: Type[db.Model]):
    class SrgNamed(Timestamp):
        id: int = Column(Integer, primary_key=True, autoincrement=True)
        version: str = Column(Text, nullable=False)
        obf: str = Column(Text, nullable=False)
        srg: str = Column(Text, nullable=False)

        locked: bool = Column(Boolean, default=False)

        @declared_attr
        def last_change_id(self) -> int:
            return Column('last_change_id', Integer, ForeignKey(f"{history_table.__tablename__}.id"))

        @declared_attr
        def last_change(self) -> _SrgHistory:
            return relationship(history_table, primaryjoin=lambda: history_table.id == self.last_change_id)

        # __table_args__ = (
        #     UniqueConstraint(version, srg),
        # )

        def to_json(self):
            return dict(
                version=self.version,
                obf=self.obf,
                srg=self.srg,
                name=self.last_change.mcp if self.last_change is not None else None,
                locked=self.locked
            )

    return SrgNamed


@generic_repr
class MethodHistory(db.Model, _SrgHistory):
    pass


@generic_repr
class Methods(db.Model, _SrgNamed(MethodHistory)):
    srg_id: str = Column(Text, nullable=False)
    signature: str = Column(Text, nullable=False)

    class_id = Column(Integer, ForeignKey("classes.id"))
    owner = relationship("Classes", back_populates='methods')

    parameters: List[Parameters] = relationship("Parameters", back_populates='method')
    clas: Classes = relationship("Classes", back_populates='methods')


@generic_repr
class FieldHistory(db.Model, _SrgHistory):
    pass


@generic_repr
class Fields(db.Model, _SrgNamed(FieldHistory)):
    srg_id: str = Column(Text, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))
    clas = relationship("Classes", back_populates='fields')


@generic_repr
class ParameterHistory(db.Model, _SrgHistory):
    pass


@generic_repr
class Parameters(db.Model, _SrgNamed(ParameterHistory)):
    method_id = Column(Integer, ForeignKey('methods.id'), nullable=False)
    method: Methods = relationship("Methods", back_populates='parameters')


db.Model.metadata.create_all(db.engine)
