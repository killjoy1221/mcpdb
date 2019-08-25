from typing import Union

from mcpdb import models

overwrite_name = "overwrite_name"

all_permissions = (
    overwrite_name,
)


def check_permission(user: Union[models.Users, models.Tokens], permission: str):
    for p in user.permissions:
        if p.name == permission:
            return True
    return False
