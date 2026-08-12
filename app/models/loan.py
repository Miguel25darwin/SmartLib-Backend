"""
Entité `loans` — emprunts.

Règle métier clé (Cahier d'Architecture §5.1) : un emprunt porte SOIT sur un
exemplaire physique (copy_id), SOIT sur une ressource numérique
(digital_resource_id), jamais les deux, jamais aucun des deux.
Imposé au niveau base de données via une CheckConstraint.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import LoanStatus

if TYPE_CHECKING:
    from app.models.copy import Copy
    from app.models.digital_resource import DigitalResource
    from app.models.user import User


class Loan(Base, TimestampMixin):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "(copy_id IS NOT NULL AND digital_resource_id IS NULL) OR "
            "(copy_id IS NULL AND digital_resource_id IS NOT NULL)",
            name="ck_loan_exactly_one_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    copy_id: Mapped[int | None] = mapped_column(
        ForeignKey("copies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    digital_resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("digital_resources.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[LoanStatus] = mapped_column(
        SAEnum(LoanStatus, name="loan_status"), nullable=False, default=LoanStatus.ACTIVE
    )

    user: Mapped["User"] = relationship(back_populates="loans")
    copy: Mapped["Copy | None"] = relationship(back_populates="loans")
    digital_resource: Mapped["DigitalResource | None"] = relationship(back_populates="loans")

    def __repr__(self) -> str:
        target = f"copy={self.copy_id}" if self.copy_id else f"digital={self.digital_resource_id}"
        return f"<Loan id={self.id} user={self.user_id} {target} status={self.status.value}>"
