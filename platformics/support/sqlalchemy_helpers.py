from sqlalchemy import inspect
from sqlalchemy.orm import ColumnProperty
from sqlalchemy_utils import get_primary_keys

from platformics.database.models.base import Base


def model_class_cols(model_cls):
    cols = []
    relationships = model_cls.__mapper__.relationships
    for col in model_cls.__mapper__.all_orm_descriptors:
        # Don't send related fields to cerbos for authz checks
        if col.key in relationships:
            continue
        cols.append(col)
    return cols


def get_primary_key(model) -> tuple[str, ColumnProperty]:
    pks = get_primary_keys(model)
    # Only use the PK for the leaf table.
    pks = {k: v for k, v in pks.items() if v.table.name == model.__table__.name}
    if len(pks) != 1:
        raise Exception(f"Expected exactly one primary key for {model.__name__}")
    for k, _ in pks.items():
        return k, getattr(model, k)
    raise Exception("PK definition missing")


def get_relationship(cls, field):
    mapper = inspect(cls)
    relationship = mapper.relationships[field]
    return relationship


# TODO FIXME THIS IS TOO OPEN. THIS SHOULD BE LOCKED DOWN TO ONLY ACCEPTABLE TYPES.
def get_orm_class_by_name(class_name: str) -> Base:
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls.__name__ == class_name:
            # Don't allow abstract classes to be manipulated directly
            # if cls.abstract:
            #     continue
            return cls
    raise Exception("Invalid class name")
