from aiogram.fsm.state import State, StatesGroup


class ManagerOrderState(StatesGroup):
    city = State()
    client_name = State()
    client_phone = State()
    address = State()
    service_type = State()
    price = State()
    date = State()
    time = State()


class ManagerAuthState(StatesGroup):
    waiting_password = State()


class AdminCreateUserState(StatesGroup):
    role = State()
    telegram_id = State()
    full_name = State()
    username = State()
    city = State()


class CleanerPaymentState(StatesGroup):
    waiting_requisites = State()
