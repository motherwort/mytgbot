from os import environ
from dotenv import load_dotenv


load_dotenv()

TOKEN = environ.get("TOKEN")
DB_NAME = environ.get("DB_NAME")

REDIS_HOST = environ.get("REDIS_HOST")
REDIS_PORT = environ.get("REDIS_PORT")
REDIS_PASS = environ.get("REDIS_PASS")
