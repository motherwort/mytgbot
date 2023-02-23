from bot import bot
from models import init_db


if __name__ == '__main__':
    print("DB connection...")
    db = init_db()
    db.close()

    print("Bot is running") 
    bot.infinity_polling()
