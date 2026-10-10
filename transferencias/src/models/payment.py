from sqlalchemy import BigInteger, CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.payment_method import PaymentMethod
from models.payment_status import PaymentStatus


class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True)
    payment_key = Column(CHAR(36), nullable=False)
    company_key = Column(CHAR(36), nullable=False)
    account_key = Column(CHAR(36), nullable=False)
    method_id = Column(Integer, ForeignKey(PaymentMethod.id), nullable=False)
    status_id = Column(Integer, ForeignKey(PaymentStatus.id), nullable=False)
    amount_minor = Column(BigInteger, nullable=False)
    fee_bps = Column(Integer, nullable=False)
    release_at = Column(DateTime(timezone=True), nullable=False)
    transaction_key = Column(CHAR(36))
    idempotency_key = Column(String(50), nullable=False)
    payload_hash = Column(CHAR(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("payment_key"),
        UniqueConstraint("transaction_key"),
        UniqueConstraint("company_key", "idempotency_key", name="uq_payment_idempotency"),
    )

    method = relationship("PaymentMethod", foreign_keys=[method_id], lazy="selectin")
    status = relationship("PaymentStatus", foreign_keys=[status_id], lazy="selectin")
