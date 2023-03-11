from telebot import TeleBot, types
import redis
import config
from models import db, User, Message
import time
from collections import defaultdict 
from enum import Enum


bot = TeleBot(config.TOKEN)
redis_client = redis.StrictRedis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT, 
    password=config.REDIS_PASS,
    decode_responses=True
)


class States(Enum):
    MENU = 1
    SEND_USERNAME = 2
    SEND_TEXT = 3
    SEND_SUCCESS = 4
    VIEW_INBOX = 5
    VIEW_ALL_INBOX = 6


class Buttons(Enum):
    VIEW_ALL = "Показать все"
    BACK = "Назад"
    SEND = "Отправить анонимное сообщение"
    SEE_INBOX = "Посмотреть входящие"


state_transitions = {
    States.MENU: defaultdict(lambda: States.MENU,
        {
            Buttons.SEND: States.SEND_USERNAME,
            Buttons.SEE_INBOX: States.VIEW_INBOX,
        }
    ),
    States.SEND_USERNAME: defaultdict(lambda: States.SEND_TEXT),
    States.SEND_TEXT: defaultdict(lambda: States.SEND_SUCCESS),
    States.SEND_SUCCESS: defaultdict(lambda: States.MENU),
    States.VIEW_INBOX: defaultdict(lambda: States.MENU,
        {
            Buttons.BACK: States.MENU,
            Buttons.VIEW_ALL: States.VIEW_ALL_INBOX,
        }
    ),
    States.VIEW_ALL_INBOX: defaultdict(lambda: States.MENU),
}


def parse_button(message_text):
    for button in Buttons:
        if message_text.startswith(button.value):
            return button
    return None


def get_user_state(username):
    return States(int(redis_client.get(f"{username}:state")))


def set_user_state(username, state: States):
    redis_client.set(f"{username}:state", state.value)


def remember_whom_to_send(username, send_to_username):
    redis_client.set(f"{username}:send_to", send_to_username)


def get_whom_to_send(username):
    return redis_client.get(f"{username}:send_to")


def reset_whom_to_send(username):
    redis_client.delete(f"{username}:send_to")


def menu_routine(bot, message):
    db.connect()
    user, _ = User.get_or_create(username=message.chat.username.lower())
    inbox_count = user.inbox.select().where(Message.unread==True).count()
    db.close()

    reset_whom_to_send(message.chat.username.lower())

    markup = (
        types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        .add("Отправить анонимное сообщение")
        .add(f"Посмотреть входящие (+{inbox_count})")
    )
    bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)


def send_username(bot, message):
    bot.send_message(message.chat.id, "Отправьте username пользователя тг", reply_markup=types.ReplyKeyboardRemove())


def send_text(bot, message):
    if message.text.startswith("@"):
        send_to_username = message.text[1:]
    else:
        send_to_username = message.text

    send_to_username = send_to_username.split(" ")
    if len(send_to_username) != 1:
        raise Exception
    else:
        send_to_username = send_to_username[0]

    db.connect()
    send_to, _ = User.get_or_create(username=send_to_username.lower())
    db.close()

    remember_whom_to_send(message.chat.username.lower(), send_to.id)

    bot.send_message(message.chat.id, f"Отправьте сообщение для пользователя @{send_to.username}")


def send_success(bot, message):
    send_to = get_whom_to_send(message.chat.username.lower())
    db.connect()
    from_user = User.get(username=message.chat.username.lower())
    to_user = User.get(id=send_to)
    Message.create(
        from_username=from_user,
        to_username=to_user,
        text=message.text
    )
    db.close()

    markup = (
        types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        .add("Зашибись")
    )

    bot.send_message(message.chat.id, f"Сообщение для пользователя @{to_user.username} сохранено. Чтобы прочитать его, необходимо будет запустить бота", reply_markup=markup)


def view_inbox(bot, message):
    db.connect()
    user = User.get(username=message.chat.username.lower())
    inbox = user.inbox.select().where(Message.unread==True).order_by(Message.datetime.asc())
    if inbox.count() > 0:
        for inbox_message in inbox:
            bot.send_message(message.chat.id, f"_{inbox_message.text}_ ({inbox_message.datetime})", parse_mode='Markdown', reply_markup=(
                types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                .add("Показать все")
                .add("Назад")
            ))
            inbox_message.unread = False
            inbox_message.save()
    else:
        bot.send_message(message.chat.id, "У вас нет непрочитанных сообщений!", reply_markup=(
            types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            .add("Показать все")
            .add("Назад")
        ))
    db.close()


def view_all_inbox(bot, message):
    db.connect()
    user = User.get(username=message.chat.username.lower())
    inbox = user.inbox.order_by(Message.datetime.asc())
    if inbox.count() > 0:
        for inbox_message in inbox:
            bot.send_message(message.chat.id, f"_{inbox_message.text}_\n({inbox_message.datetime})", parse_mode='Markdown', reply_markup=(
                types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add("Назад")
            ))
            inbox_message.unread = False
            inbox_message.save()
    else:
        bot.send_message(message.chat.id, "Вам никто не присылал сообщений 😢", reply_markup=(
            types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            .add("😭")
        ))
    db.close()


state_action = {
    States.MENU: menu_routine,
    States.SEND_USERNAME: send_username,
    States.SEND_TEXT: send_text,
    States.SEND_SUCCESS: send_success,
    States.VIEW_INBOX: view_inbox,
    States.VIEW_ALL_INBOX: view_all_inbox,
    # States.VIEW_SENT: view_sent,
}


@bot.message_handler(func=lambda message: True)
def routine(message):
    if message.text == "/start":
        bot.send_message(message.chat.id, "Сейчас всё объясню", reply_markup=types.ReplyKeyboardRemove())
        time.sleep(0.75)
        bot.send_message(message.chat.id, "Короче это...")
        time.sleep(0.75)
        new_state = States.MENU
    else:
        state = get_user_state(message.chat.username.lower())
        button = parse_button(message.text)
        new_state = state_transitions[state][button]
    set_user_state(message.chat.username.lower(), new_state)
    try:
        state_action[new_state](bot, message)
    except:
        bot.send_message(message.chat.id, "Не ломай мне бота! 😡")
        time.sleep(0.75)
        bot.send_message(message.chat.id, "По новой", reply_markup=(
            types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add("🫡")
        ))
        new_state = States.MENU
        set_user_state(message.chat.username.lower(), new_state)
