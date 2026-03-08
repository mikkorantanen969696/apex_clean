from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CLEANER = "cleaner"


class OrderStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    DONE = "done"
    PAID = "paid"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID_TO_CLEANER = "paid_to_cleaner"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"), nullable=True)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    city: Mapped["City | None"] = relationship(back_populates="users")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    users: Mapped[list[User]] = relationship(back_populates="city")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cleaner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255))
    client_phone: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(Text)
    service_type: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.NEW, index=True)
    chat_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (UniqueConstraint("order_id", name="uq_photos_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    photo_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_after: Mapped[str | None] = mapped_column(Text, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("order_id", name="uq_payments_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    amount: Mapped[float] = mapped_column(Float)
    paid_to_cleaner: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_from_client: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ServiceConfig(Base):
    __tablename__ = "service_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_price: Mapped[float] = mapped_column(Float, default=0.0)
    cleaner_commission_percent: Mapped[float] = mapped_column(Float, default=70.0)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
