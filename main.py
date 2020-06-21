from pathlib import Path
from pyrogram import Client, MessageHandler
from configparser import ConfigParser
import inquirer
import time

session_name = "default"
phone_number = None
password = None
force_sms = False
as_copy = False

parser = ConfigParser()
parser.read(str(Path("./config.ini")))
if parser.has_section("extra"):
    session_name = (
        parser.has_option("extra", "session_name")
        and parser.get("extra", "session_name")
        or "default"
    )
    phone_number = (
        parser.has_option("extra", "phone_number")
        and parser.get("extra", "phone_number")
        or None
    )
    password = (
        parser.has_option("extra", "password")
        and parser.get("extra", "password")
        or None
    )
    force_sms = (
        parser.has_option("extra", "force_sms")
        and parser.getboolean("extra", "force_sms")
        or False
    )
    as_copy = (
        parser.has_option("extra", "as_copy")
        and parser.getboolean("extra", "as_copy")
        or False
    )

if not Path(session_name + ".session").exists():
    if phone_number is None:
        raise ValueError("phone_number must be set for a new session")
    if password is None:
        raise ValueError("password must be set for a new session")

app = Client(
    session_name=session_name,
    phone_number=phone_number,
    password=password,
    force_sms=force_sms,
)


def now():
    return time.strftime("%H:%M:%S", time.localtime())


settings = ConfigParser()
settings.read(str(Path("./settings.ini")))
msg_id = None
if settings.has_section("main"):
    msg_id = (
        settings.has_option("main", "last_msg_id")
        and settings.getint("main", "last_msg_id")
        or None
    )
else:
    settings.add_section("main")

with app:
    dialogs = app.get_dialogs()
    chats = []

    for dialog in dialogs:
        if dialog.chat.type != "channel":
            continue
        chats.append((dialog.chat.title, dialog.chat.id))
    if len(chats) == 0:
        print("No channels to monitor")
        exit(0)
    questions = [
        inquirer.List("chat", message="Select a channel to read from", choices=chats,),
    ]
    answers = inquirer.prompt(questions)
    from_chat_id = answers["chat"]
    me = app.get_me()
    chats = [c for c in chats if c[1] != from_chat_id]
    for chat in chats:
        member = app.get_chat_member(chat[1], me.id)
        if member.status in ["creator", "administrator", "member"]:
            continue
        if member.status == "restricted" and member.can_send_messages:
            continue
        chats.remove(chat)
    if len(chats) == 0:
        print("No channels to write messages")
        exit(0)

    questions = [
        inquirer.List("chat", message="Select a channel to forward to", choices=chats,),
    ]
    answers = inquirer.prompt(questions)
    to_chat_id = answers["chat"]

    def transmitter(client, message):
        global msg_id
        if message.chat.id == from_chat_id:
            if msg_id is not None and msg_id >= message.message_id:
                print(now(), message.message_id, "- skipped")
                return
            msg_id = message.message_id
            client.forward_messages(
                chat_id=to_chat_id,
                from_chat_id=message.chat.id,
                message_ids=message.message_id,
                as_copy=as_copy,
            )
            app.read_history(from_chat_id, message.message_id)
            print(now(), message.message_id, message.text)

    app.add_handler(MessageHandler(transmitter))
    print(now(), "- session started")
    app.idle()

if msg_id is not None:
    settings.set("main", "last_msg_id", str(msg_id))
with open("settings.ini", "w") as f:
    settings.write(f)
    print()
    print("settings saved")

print()
print(now(), "- session closed")
