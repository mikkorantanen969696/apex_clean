TEXTS = {
    "ru": {
        "welcome": "Привет! Я бот управления уборками. Выберите действие ниже 👇",
        "no_access": "У вас нет доступа. Обратитесь к администратору.",
        "ask_password": "Введите пароль менеджера:",
        "auth_ok": "Авторизация успешна ✅",
        "auth_fail": "Неверный пароль ❌",
        "done": "Готово ✅",
    },
    "en": {
        "welcome": "Hi! I am a cleaning workflow bot. Choose an action 👇",
        "no_access": "Access denied. Contact administrator.",
        "ask_password": "Enter manager password:",
        "auth_ok": "Authorization successful ✅",
        "auth_fail": "Wrong password ❌",
        "done": "Done ✅",
    },
}


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)
