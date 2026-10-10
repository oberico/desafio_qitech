from sqlalchemy import CHAR, Column, Date, DateTime, Integer, String, UniqueConstraint, func

from models.base import Base


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    client_key = Column(CHAR(36), nullable=False)
    cpf = Column(CHAR(14), nullable=False)
    name = Column(String(255), nullable=False)
    birthdate = Column(Date, nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("cpf", name="client_cpf_key"),
        UniqueConstraint("email", name="client_email_key"),
    )
