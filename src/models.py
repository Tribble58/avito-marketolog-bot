from sqlalchemy import Column, Integer, TIMESTAMP, BIGINT, ForeignKey
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
    Stores TG users and all corresponding info
    """
    __tablename__ = 'users'

    tg_id = Column(BIGINT, unique=True)
    avito_id = Column(Integer, unique=True)


class UserTemplate(BaseModel):
    """
    Stores templates related to TG user
    """
    __tablename__ = 'users_templates'

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    template = Column(VARCHAR(length=1000), nullable=False)
