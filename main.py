from pathlib import Path
from pyrogram import Client, MessageHandler
from configparser import ConfigParser
import inquirer

session_name = "default"
phone_number = None
password = None
force_sms = False

parser = ConfigParser()
parser.read(str(Path("./config.ini")))
if parser.has_section("extra"):
    session_name = parser.has_option("extra", "session_name") and parser.get("extra", "session_name") or "default"
    phone_number = parser.has_option("extra", "phone_number") and parser.get("extra", "phone_number") or None
    password = parser.has_option("extra", "password") and parser.get("extra", "password") or None
    force_sms = parser.has_option("extra", "force_sms") and parser.getboolean("extra", "force_sms") or False

if not Path(session_name + ".session").exists():
    if phone_number is None:
        raise ValueError("phone_number must be set for new session")
    if password is None:
        raise ValueError("password must be set for new session")

app = Client(session_name=session_name,
             phone_number=phone_number,
             password=password,
             force_sms=force_sms
             )

with app:
    dialogs = app.get_dialogs()
    chats = []

    for dialog in dialogs:
        if dialog.chat.type != 'channel':
            continue
        chats.append((dialog.chat.title, dialog.chat.id))
    if len(chats) == 0:
        print('No channels to monitor')
        exit(0)
    questions = [
        inquirer.List('chat',
                      message="Select a channel to read from",
                      choices=chats,
                      ),
    ]
    answers = inquirer.prompt(questions)
    from_chat_id = answers['chat']
    me = app.get_me()
    chats = [c for c in chats if c[1] != from_chat_id]
    for chat in chats:
        member = app.get_chat_member(chat[1], me.id)
        if member.status in ['creator', 'administrator', 'member']:
            continue
        if member.status == 'restricted' and member.can_send_messages:
            continue
        chats.remove(chat)
    if len(chats) == 0:
        print('No channels to write messages')
        exit(0)

    questions = [
        inquirer.List('chat',
                      message="Select a channel to forward to",
                      choices=chats,
                      ),
    ]
    answers = inquirer.prompt(questions)
    to_chat_id = answers['chat']


    def transmitter(client, message):
        if message.chat.id == from_chat_id:
            client.forward_messages(
                chat_id=to_chat_id,
                from_chat_id=message.chat.id,
                message_ids=message.message_id,
                as_copy=True
            )
            app.read_history(from_chat_id, message.message_id)


    app.add_handler(MessageHandler(transmitter))

    app.idle()
