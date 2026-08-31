import sqlite3
import telebot
import json
import pandas as pd
from config import TOKEN, HIGH_ACCESS, SKIP_REASONS
from markup import basicMarkup, hide_keyboard
from sus import get_id_hash, encrypt_value, decrypt_value
from datetime import datetime
from zoneinfo import ZoneInfo

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect('group.db', check_same_thread=False)

def addingGroupmate(name, sur, nick):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS groupmates (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, nick TEXT, userID_enc TEXT, userID_hash TEXT, points int)")
    conn.commit()
    nameTable = encrypt_value(name)
    surTable = encrypt_value(sur)
    nickTable = encrypt_value(nick)
    cur.execute('INSERT INTO groupmates (name, surname, nick, points) VALUES(?, ?, ?, ?)', (nameTable, surTable, nickTable, 15))
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
    bot.send_message(message.chat.id, "Введи дату в формате: ДД.ММ", reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, regDate, idy)


def regDate(message, idy, finDate=None, dayOfWeek=None):
    if finDate is None:
        try:
            date_obj = datetime.strptime(f"2026.{message.text}", "%Y.%d.%m")
        except Exception:
            bot.send_message(message.chat.id, "Правильно введи дату!")
            skipPair(message, idy)
            return
        moscow_tz = ZoneInfo("Europe/Moscow")
        now_moscow = datetime.now(moscow_tz)
        today = now_moscow.replace(year=2026, hour=0, minute=0, second=0, microsecond=0)
        end_of_year = datetime(year=2026, month=12, day=31, tzinfo=moscow_tz)
        user_date = date_obj.replace(year=2026, tzinfo=moscow_tz)
        dayOfWeek = date_obj.weekday()
        if not (today <= user_date <= end_of_year) or dayOfWeek == 6:
            bot.send_message(message.chat.id, "Дата в недопустимом диапазоне или это воскресенье!")
            skipPair(message, idy)
            return
        finDate = date_obj.strftime("%m-%d")

    with open("timetable.json", "r", encoding="utf-8") as file:
        timetable = json.load(file)
    paraMarkup = telebot.types.ReplyKeyboardMarkup()
    daysPary = timetable[str(dayOfWeek)]
    for paraT in list(daysPary.values()):
        btncur = telebot.types.KeyboardButton(paraT)
        paraMarkup.row(btncur)
    bot.send_message(message.chat.id, "Выбери пару", reply_markup=paraMarkup)
    bot.register_next_step_handler(message, regPara, idy, finDate, dayOfWeek)


def regPara(message, idy, finDate, dayOfWeek, para=None):
    if para is None:
        with open("timetable.json", "r", encoding="utf-8") as file:
            timetable = json.load(file)
        listikVar = list(timetable[str(dayOfWeek)].values())
        if message.text not in listikVar:
            bot.send_message(message.chat.id, "Что ты написюкал?")
            regDate(message, idy, finDate, dayOfWeek)
            return
        para = int(message.text.split(".")[0])

    reasonMarkup = telebot.types.ReplyKeyboardMarkup()
    for paraT in SKIP_REASONS:
        btncur = telebot.types.KeyboardButton(paraT)
        reasonMarkup.row(btncur)
    bot.send_message(message.chat.id, "Выбери причину", reply_markup=reasonMarkup)
    bot.register_next_step_handler(message, regReason, idy, finDate, dayOfWeek, para)


def regReason(message, idy, finDate, dayOfWeek, para):
    if message.text not in SKIP_REASONS:
        bot.send_message(message.chat.id, "Ну ты тыкни в кнопку!")
        regPara(message, idy, finDate, dayOfWeek, para)
        return
    reason = SKIP_REASONS.index(message.text)
    cur = conn.cursor()
    cur.execute("SELECT id FROM skips WHERE idPerson = ? AND date = ? AND (para = ? OR para = ?)", (idy, finDate, 0, para))
    listikExisting = cur.fetchall()
    if len(listikExisting) != 0:
        bot.send_message(message.chat.id, "Запись про пару уже была добавлена", reply_markup=basicMarkup)
    else:
        cur.execute('INSERT INTO skips (idPerson, date, para, reason) VALUES(?, ?, ?, ?)', (idy, finDate, para, reason))
        conn.commit()
        bot.send_message(message.chat.id, "Запись про пару добавлена", reply_markup=basicMarkup)
    cur.close()



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