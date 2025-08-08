from sqlalchemy import Column, Integer, TIMESTAMP, BIGINT, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.functions import now

Base = declarative_base()


class BaseModel(Base):
    """
    Base model for storing attributes
    """
    __abstract__ = True

    id = Column(Integer, nullable=False, unique=True, primary_key=True, autoincrement=True)
    created_at = Column(TIMESTAMP, nullable=False, default=now())
    updated_at = Column(TIMESTAMP, nullable=False, default=now())


class User(BaseModel):
    """
    Stores Users and all corresponding info
    """
    __tablename__ = 'users'

    tg_id = Column(BIGINT, unique=True)


class UserTemplate(BaseModel):
    """
    Stores templates related to User
    """
    __tablename__ = 'users_templates'

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    template = Column(VARCHAR(length=1000), nullable=False)


class Account(BaseModel):
    """
    Stores Accounts related to User. Business meaning: Avito clients that User manages
    """
    __tablename__ = 'accounts'

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    avito_id = Column(Integer, nullable=False)
    name = Column(VARCHAR(length=1000))
    number = Column(VARCHAR(length=1000))
    client_id = Column(VARCHAR(length=1000))
    client_secret = Column(VARCHAR(length=1000))

    __table_args__ = (
        UniqueConstraint("user_id", "avito_id", name="uq_accounts"),
    )
