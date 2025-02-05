"""
Test factory bases
"""

import factory
import faker
import sqlalchemy as sa
import uuid6
from factory import Faker, fuzzy
from faker_biology.bioseq import Bioseq
from faker_biology.physiology import Organ
from faker_enum import EnumProvider

from platformics.database.models import Entity

Faker.add_provider(Bioseq)
Faker.add_provider(Organ)
Faker.add_provider(EnumProvider)


class SessionStorage:
    """
    TODO: this is a lame singleton to prevent this library from requiring an active SA session at import-time. We
    should try to refactor it out when we know more about factoryboy
    """

    session = None

    @classmethod
    def set_session(cls, session: sa.orm.Session) -> None:
        cls.session = session

    @classmethod
    def get_session(cls) -> sa.orm.Session | None:
        return cls.session


class CommonFactory(factory.alchemy.SQLAlchemyModelFactory):
    """
    Base class for all factories
    """

    owner_user_id = fuzzy.FuzzyInteger(1, 1000)
    collection_id = fuzzy.FuzzyInteger(1, 1000)
    entity_id = uuid6.uuid7()  # needed so we can set `sqlalchemy_get_or_create` = entity_id in other factories

    class Meta:
        sqlalchemy_session_factory = SessionStorage.get_session
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None  # workaround for a bug in factoryboy
