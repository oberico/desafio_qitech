from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.client import Client


class Company(Base):
    __tablename__ = "company"

    id = Column(Integer, primary_key=True)
    company_key = Column(CHAR(36), nullable=False)
    cnpj = Column(CHAR(18), nullable=False)
    legal_name = Column(String(255), nullable=False)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("company_key"),
        UniqueConstraint("cnpj", name="company_cnpj_key"),
    )

    account = relationship("Account", uselist=False, back_populates="company", lazy="selectin")
