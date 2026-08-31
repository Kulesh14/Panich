import sqlite3
import telebot
import pandas as pd
from config import TOKEN, HIGH_ACCESS
from markup import basicMarkup
from sus import get_id_hash, encrypt_value, decrypt_value

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect('group.db', check_same_thread=False)

def addingGroupmate(name, sur, nick):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS groupmates (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, nick TEXT, userID_enc TEXT, userID_hash TEXT, points int)")
    conn.commit()
    nameTable = encrypt_value(name)
    surTable = encrypt_value(sur)
    nickTable = encrypt_value(nick)
    cur.execute(f'INSERT INTO groupmates (name, surname, nick, points) VALUES(?, ?, ?, ?)', (nameTable, surTable, nickTable, 15))
    conn.commit()
    #print(decrypt_value(nameTable), decrypt_value(surTable), decrypt_value(nickTable))
    cur.close()


def createTable():
    df = pd.read_csv('groupmates.csv', sep=';', encoding='utf-8', header=None)
    for i in range(len(df)):
        addingGroupmate(df.iloc[i, 0], df.iloc[i, 1], df.iloc[i, 2])


@bot.message_handler(commands=['start'])
def start(message):
    cur = conn.cursor()
    nick = message.chat.username
    cur.execute("SELECT id, nick FROM groupmates WHERE userID_hash IS NULL")
    listikOfFreeNicks = cur.fetchall()
    for i in range(len(listikOfFreeNicks)):
        if nick == decrypt_value(listikOfFreeNicks[i][1]):
            cur.execute("UPDATE groupmates SET userID_enc = ?, userID_hash = ? WHERE id = ?", (encrypt_value(str(message.chat.id)), get_id_hash(str(message.chat.id)), listikOfFreeNicks[i][0]))
            conn.commit()
            bot.send_message(message.chat.id, "Вы успешно зарегистрированы!", reply_markup=basicMarkup)
            break
    cur.close()


@bot.message_handler()
def anyMess(message):
    cur = conn.cursor()
    idHash = get_id_hash(str(message.chat.id))
    cur.execute("SELECT id FROM groupmates WHERE userID_hash = ?", (idHash, ))
    listikID = cur.fetchall()
    cur.close()
    if len(listikID) == 0:
        return
    idishnik = listikID[0][0]
    if message.text in ['Пропуск пары']:
        skipPair(message, idishnik)
    elif message.text in ['Пропуск дня']:
        skipDay(message, idishnik)
    elif message.text in ['Пропуск периода']:
        skipPeriod(message, idishnik)
    elif message.text in ['Статистика']:
        statistics(message, idishnik)
    elif message.text in ['Реклама']:
        advertisment(message)
    else:
        boobs(message)


def skipPair(message, idy):
    bot.send_message(message.chat.id, "Запись про пару добавлена", reply_markup=basicMarkup)


def skipDay(message, idy):
    bot.send_message(message.chat.id, "Запись про день добавлена", reply_markup=basicMarkup)


def skipPeriod(message, idy):
    bot.send_message(message.chat.id, "Запись про период добавлена", reply_markup=basicMarkup)


def statistics(message, idy):
    cur = conn.cursor()
    cur.execute("SELECT nick FROM groupmates WHERE id = ?", (idy, ))
    nicky = decrypt_value(cur.fetchall()[0][0])
    cur.close()
    if nicky in HIGH_ACCESS:
        bot.send_message(message.chat.id, "У вас есть доступ к статистике", reply_markup=basicMarkup)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к статистике", reply_markup=basicMarkup)


def advertisment(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton('Перейти на Рыфмач', url="https://ryfmach.by/")
    markup.add(btn1)
    bot.send_message(message.chat.id, "Снизу кнопка для перехода", reply_markup=markup)
    bot.send_message(message.chat.id, "Ну давай, рассказывай, когда тебя не будет", reply_markup=basicMarkup)


def boobs(message):
    with open("image.png", "rb") as photo:
        bot.send_photo(chat_id=message.chat.id, photo=photo)
    bot.send_message(message.chat.id, "Ну давай, рассказывай, когда тебя не будет", reply_markup=basicMarkup)


bot.polling(non_stop=True)