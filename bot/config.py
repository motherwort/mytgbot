from os import environ
from dotenv import load_dotenv


load_dotenv()

TOKEN = environ.get("TOKEN")
DB_NAME = environ.get("DB_NAME")
USER_STATUS_SHELVE = environ.get("USER_STATUS_SHELVE")
USER_SEND_TO_SHELVE = environ.get("USER_SEND_TO_SHELVE")
