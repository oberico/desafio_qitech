from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.account_class import AccountClass
from models.account_status import AccountStatus
from models.base import Base


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    code = Column(String(20))
    company_id = Column(Integer, ForeignKey("company.id"))
    class_id = Column(Integer, ForeignKey(AccountClass.id), nullable=False)
    status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=False)
    normal_balance = Column(CHAR(1), nullable=False)
    currency = Column(String(3), nullable=False, server_default="brl")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("account_key"),
        UniqueConstraint("code"),
        UniqueConstraint("company_id", name="account_company_id_key"),
    )

    status = relationship("AccountStatus", foreign_keys=[status_id], lazy="selectin")
    company = relationship("Company", back_populates="account", lazy="selectin")
