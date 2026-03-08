from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from database.models import (
    AuditLog,
    City,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Role,
    ServiceConfig,
    User,
)


class Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(self, actor_telegram_id: int, action: str, details: str) -> None:
        self.session.add(AuditLog(actor_telegram_id=actor_telegram_id, action=action, details=details))
        await self.session.commit()

    async def get_user_by_tg(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def upsert_telegram_user(self, telegram_id: int, username: str | None, full_name: str) -> User:
        user = await self.get_user_by_tg(telegram_id)
        if user:
            user.username = username
            user.full_name = full_name
        else:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=Role.CLEANER,
                active=False,
            )
            self.session.add(user)
        await self.session.commit()
        return user

    async def list_cities(self) -> list[City]:
        result = await self.session.execute(select(City).order_by(City.name))
        return list(result.scalars().all())

    async def add_city(self, name: str, topic_id: int | None = None) -> City:
        city = City(name=name, topic_id=topic_id)
        self.session.add(city)
        await self.session.commit()
        return city

    async def create_or_update_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str,
        role: Role,
        active: bool = True,
        password_hash: str | None = None,
        city_id: int | None = None,
    ) -> User:
        user = await self.get_user_by_tg(telegram_id)
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role,
                active=active,
                password_hash=password_hash,
                city_id=city_id,
            )
            self.session.add(user)
        else:
            user.username = username or user.username
            user.full_name = full_name
            user.role = role
            user.active = active
            user.city_id = city_id
            if password_hash:
                user.password_hash = password_hash
        await self.session.commit()
        return user

    async def deactivate_user(self, telegram_id: int) -> bool:
        user = await self.get_user_by_tg(telegram_id)
        if not user:
            return False
        user.active = False
        await self.session.commit()
        return True

    async def create_order(
        self,
        city_id: int,
        manager_id: int,
        client_name: str,
        client_phone: str,
        address: str,
        service_type: str,
        price: float,
        scheduled_at: datetime,
    ) -> Order:
        order = Order(
            city_id=city_id,
            manager_id=manager_id,
            client_name=client_name,
            client_phone=client_phone,
            address=address,
            service_type=service_type,
            price=price,
            scheduled_at=scheduled_at,
            status=OrderStatus.NEW,
        )
        self.session.add(order)
        await self.session.flush()

        payment = Payment(order_id=order.id, amount=price, status=PaymentStatus.PENDING)
        self.session.add(payment)
        await self.session.commit()
        return order

    async def assign_cleaner(self, order_id: int, cleaner_id: int) -> Order | None:
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order or order.status != OrderStatus.NEW:
            return None
        order.cleaner_id = cleaner_id
        order.status = OrderStatus.ACCEPTED
        await self.session.commit()
        return order

    async def complete_order(self, order_id: int) -> Order | None:
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return None
        order.status = OrderStatus.DONE
        await self.session.commit()
        return order

    async def mark_paid_to_cleaner(self, order_id: int) -> bool:
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if not payment:
            return False
        payment.paid_to_cleaner = True
        payment.status = PaymentStatus.PAID_TO_CLEANER

        order_res = await self.session.execute(select(Order).where(Order.id == order_id))
        order = order_res.scalar_one_or_none()
        if order:
            order.status = OrderStatus.PAID
        await self.session.commit()
        return True

    async def confirm_client_payment(self, order_id: int) -> bool:
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if not payment:
            return False
        payment.paid_from_client = True
        payment.status = PaymentStatus.CONFIRMED
        await self.session.commit()
        return True

    async def list_new_orders_for_city(self, city_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order).where(Order.city_id == city_id, Order.status == OrderStatus.NEW).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_manager_orders(self, manager_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order).where(Order.manager_id == manager_id).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def stats_summary(self, manager_id: int | None = None) -> dict[str, Any]:
        where_clause = [True]
        if manager_id is not None:
            where_clause = [Order.manager_id == manager_id]

        status_query = select(
            func.count(Order.id),
            func.sum(case((Order.status == OrderStatus.NEW, 1), else_=0)),
            func.sum(case((Order.status == OrderStatus.ACCEPTED, 1), else_=0)),
            func.sum(case((Order.status == OrderStatus.DONE, 1), else_=0)),
            func.sum(case((Order.status == OrderStatus.PAID, 1), else_=0)),
            func.coalesce(func.sum(Order.price), 0.0),
        ).where(*where_clause)
        result = await self.session.execute(status_query)
        total, new_cnt, accepted_cnt, done_cnt, paid_cnt, revenue = result.one()
        return {
            "total": int(total or 0),
            "new": int(new_cnt or 0),
            "accepted": int(accepted_cnt or 0),
            "done": int(done_cnt or 0),
            "paid": int(paid_cnt or 0),
            "revenue": float(revenue or 0.0),
        }

    async def export_orders(self, manager_id: int | None = None) -> list[dict[str, Any]]:
        cleaner_alias = aliased(User)
        query: Select[tuple[Order, City, User, User | None]] = (
            select(Order, City, User, cleaner_alias)
            .join(City, Order.city_id == City.id)
            .join(User, Order.manager_id == User.id)
            .outerjoin(cleaner_alias, Order.cleaner_id == cleaner_alias.id)
            .order_by(Order.created_at.desc())
        )
        if manager_id is not None:
            query = query.where(Order.manager_id == manager_id)

        rows = await self.session.execute(query)
        result: list[dict[str, Any]] = []
        for order, city, manager, cleaner in rows.all():
            result.append(
                {
                    "order_id": order.id,
                    "city": city.name,
                    "manager": manager.full_name,
                    "cleaner": cleaner.full_name if cleaner else "",
                    "client_name": order.client_name,
                    "client_phone": order.client_phone,
                    "address": order.address,
                    "service_type": order.service_type,
                    "price": order.price,
                    "status": order.status.value,
                    "scheduled_at": order.scheduled_at.isoformat(sep=" ", timespec="minutes"),
                    "created_at": order.created_at.isoformat(sep=" ", timespec="minutes"),
                }
            )
        return result

    async def get_or_create_service_config(self) -> ServiceConfig:
        result = await self.session.execute(select(ServiceConfig).where(ServiceConfig.id == 1))
        config = result.scalar_one_or_none()
        if not config:
            config = ServiceConfig(id=1, default_price=0.0, cleaner_commission_percent=70.0)
            self.session.add(config)
            await self.session.commit()
        return config

    async def update_service_config(self, default_price: float | None, commission: float | None) -> ServiceConfig:
        config = await self.get_or_create_service_config()
        if default_price is not None:
            config.default_price = default_price
        if commission is not None:
            config.cleaner_commission_percent = commission
        await self.session.commit()
        return config
