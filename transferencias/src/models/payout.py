from sqlalchemy import BigInteger, CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base import Base
from models.payout_purpose import PayoutPurpose
from models.payout_status import PayoutStatus


class Payout(Base):
    __tablename__ = "payout"

    id = Column(Integer, primary_key=True)
    payout_key = Column(CHAR(36), nullable=False)
    company_key = Column(CHAR(36), nullable=False)
    account_key = Column(CHAR(36), nullable=False)
    purpose_id = Column(Integer, ForeignKey(PayoutPurpose.id), nullable=False)
    destination = Column(JSONB, nullable=False)
    status_id = Column(Integer, ForeignKey(PayoutStatus.id), nullable=False)
    amount_minor = Column(BigInteger, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True))
    failure_reason = Column(String(255))
    transaction_key = Column(CHAR(36))
    idempotency_key = Column(String(50), nullable=False)
    payload_hash = Column(CHAR(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("payout_key"),
        UniqueConstraint("transaction_key"),
        UniqueConstraint("company_key", "idempotency_key", name="uq_payout_idempotency"),
    )

    purpose = relationship("PayoutPurpose", foreign_keys=[purpose_id], lazy="selectin")
    status = relationship("PayoutStatus", foreign_keys=[status_id], lazy="selectin")
