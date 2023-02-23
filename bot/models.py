from peewee import SqliteDatabase, Model, CharField, BooleanField, TextField, DateTimeField, ForeignKeyField, JOIN, fn
import config
import datetime


db = SqliteDatabase(config.DB_NAME)


class User(Model):
    username = CharField(unique=True, null=False)

    class Meta:
        table_name = "users"
        database = db


class Message(Model):
    from_username = ForeignKeyField(User, backref='sent')
    to_username = ForeignKeyField(User, backref='inbox')
    unread = BooleanField(default=True)
    text = TextField(null=False)
    datetime = DateTimeField(null=False, default=datetime.datetime.now)

    class Meta:
        table_name = "messages"
        database = db


def init_db():
    db.connect()
    db.create_tables([User, Message])
    return db
