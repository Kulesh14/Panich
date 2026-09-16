import sqlite3
import telebot
import json
import pandas as pd
from config import TOKEN, HIGH_ACCESS, SKIP_REASONS
from markup import basicMarkup, hide_keyboard
from sus import get_id_hash, encrypt_value, decrypt_value
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect('group.db', check_same_thread=False)

def addingGroupmate(name, sur, nick):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS groupmates (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, nick TEXT, userID_enc TEXT, userID_hash TEXT, points int, date DATETIME)")
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


def getSurname(idy):
    cur = conn.cursor()
    cur.execute("SELECT name FROM groupmates WHERE id = ?", (idy, ))
    listikSur = cur.fetchall()
    cur.close()
    return decrypt_value(listikSur[0][0])

@bot.message_handler(commands=['start'])
def start(message):
    cur = conn.cursor()
    nick = message.chat.username
    cur.execute("SELECT id, nick FROM groupmates WHERE userID_hash IS NULL")
    listikOfFreeNicks = cur.fetchall()
    cur.close()
    for i in range(len(listikOfFreeNicks)):
        if nick == decrypt_value(listikOfFreeNicks[i][1]):
            texty = (
                "🔒 **Безопасность и конфиденциальность**\n\n"
                "Наш бот заботится о вашей безопасности. Все ваши персональные данные "
                "(имя, фамилия, никнейм) **автоматически шифруются** при записи в базу данных. "
                "Мы не храним личную информацию в открытом виде и строго соблюдаем "
                "законодательство Республики Беларусь.\n\n"
                "Нажимая кнопку ниже, вы даете свободное и однозначное согласие на обработку "
                "ваших данных для обеспечения работы бота.\n\n"
                f"📄 Ознакомиться с правилами: [Политика конфиденциальности]"
            )
            markupT = telebot.types.InlineKeyboardMarkup()
            btn_agree = telebot.types.InlineKeyboardButton(
                text="Согласен и хочу продолжить", 
                callback_data=f"agree_privacy:{listikOfFreeNicks[i][0]}"
            )
            markupT.add(btn_agree)
            try:
                with open('Privacy_Policy.pdf', 'rb') as file:
                    bot.send_document(
                        chat_id=message.chat.id, 
                        document=file, 
                        caption=texty, 
                        parse_mode='Markdown', 
                        reply_markup=markupT
                    )
            except FileNotFoundError:
                bot.send_message(message.chat.id, "Ошибка: Файл политики не найден. Обратитесь к администратору.")
            break


@bot.callback_query_handler(func=lambda call: call.data.startswith("agree_privacy:"))
def callback_agree(call):  
    data_parts = call.data.split(':')
    idy = data_parts[1]
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    cur = conn.cursor()
    cur.execute("UPDATE groupmates SET userID_enc = ?, userID_hash = ?, date = ? WHERE id = ?", (encrypt_value(str(call.message.chat.id)), get_id_hash(str(call.message.chat.id)), current_time, idy))
    conn.commit()
    bot.send_message(call.message.chat.id, "Вы успешно зарегистрированы!", reply_markup=basicMarkup)
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
    elif message.text in ['Отменить']:
        deletePeriod(message, idishnik)
    elif message.text in ['Личная статистика']:
        personStat(message, idishnik)
    elif message.text in ['Начислить баллы']:
        pointsAdding(message, idishnik)
    elif message.text in ['Социальное положение']:
        socialRating(message)
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
        if reason == 5:
            cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
            bally = cur.fetchall()[0][0] - 5
            cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
            conn.commit()
        bot.send_message(message.chat.id, "Запись про пару добавлена", reply_markup=basicMarkup)
    cur.close()



def skipDay(message, idy):
    bot.send_message(message.chat.id, "Введи дату в формате: ДД.ММ", reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, regDate2, idy)


def regDate2(message, idy, finDate=None, dayOfWeek=None):
    if finDate is None:
        try:
            date_obj = datetime.strptime(f"2026.{message.text}", "%Y.%d.%m")
        except Exception:
            bot.send_message(message.chat.id, "Правильно введи дату!")
            skipDay(message, idy)
            return
        moscow_tz = ZoneInfo("Europe/Moscow")
        now_moscow = datetime.now(moscow_tz)
        today = now_moscow.replace(year=2026, hour=0, minute=0, second=0, microsecond=0)
        end_of_year = datetime(year=2026, month=12, day=31, tzinfo=moscow_tz)
        user_date = date_obj.replace(year=2026, tzinfo=moscow_tz)
        dayOfWeek = date_obj.weekday()
        if not (today <= user_date <= end_of_year) or dayOfWeek == 6:
            bot.send_message(message.chat.id, "Дата в недопустимом диапазоне или это воскресенье!")
            skipDay(message, idy)
            return
        finDate = date_obj.strftime("%m-%d")

    reasonMarkup = telebot.types.ReplyKeyboardMarkup()
    for paraT in SKIP_REASONS:
        btncur = telebot.types.KeyboardButton(paraT)
        reasonMarkup.row(btncur)
    bot.send_message(message.chat.id, "Выбери причину", reply_markup=reasonMarkup)
    bot.register_next_step_handler(message, regReason2, idy, finDate, dayOfWeek)


def regReason2(message, idy, finDate, dayOfWeek):
    if message.text not in SKIP_REASONS:
        bot.send_message(message.chat.id, "Ну ты тыкни в кнопку!")
        regDate2(message, idy, finDate, dayOfWeek)
        return
    reason = SKIP_REASONS.index(message.text)
    cur = conn.cursor()
    cur.execute("SELECT id FROM skips WHERE idPerson = ? AND date = ? AND para = ?", (idy, finDate, 0))
    listikExisting = cur.fetchall()
    if len(listikExisting) != 0:
        bot.send_message(message.chat.id, "Запись про день уже была добавлена", reply_markup=basicMarkup)
    else:
        cur.execute('SELECT id FROM skips WHERE idPerson = ? AND date = ? AND reason = ?', (idy, finDate, 5))
        ballyBack = len(cur.fetchall())
        cur.execute('DELETE FROM skips WHERE idPerson = ? AND date = ?', (idy, finDate))
        conn.commit()
        cur.execute('INSERT INTO skips (idPerson, date, para, reason) VALUES(?, ?, ?, ?)', (idy, finDate, 0, reason))
        conn.commit()
        if reason == 5:
            with open("timetable.json", "r", encoding="utf-8") as file:
                timetable = json.load(file)
            daysPary = timetable[str(dayOfWeek)]
            ballyMinus = len(list(daysPary.values()))
            cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
            bally = cur.fetchall()[0][0] + (ballyBack * 5) - (ballyMinus * 5)
            cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
            conn.commit()
        else:
            cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
            bally = cur.fetchall()[0][0] + (ballyBack * 5)
            cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
            conn.commit()
        bot.send_message(message.chat.id, "Запись про день добавлена", reply_markup=basicMarkup)
    cur.close()


def skipPeriod(message, idy):
    bot.send_message(message.chat.id, "Введи период в формате: ДД.ММ-ДД.ММ", reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, regDate3, idy)


def regDate3(message, idy, finDate1=None, finDate2=None):
    if finDate1 is None:
        listikDates = message.text.split('-')
        if len(listikDates) != 2:
            bot.send_message(message.chat.id, "Правильно введи дату!")
            skipPeriod(message, idy)
            return
        try:
            date_obj1 = datetime.strptime(f"2026.{listikDates[0]}", "%Y.%d.%m")
            date_obj2 = datetime.strptime(f"2026.{listikDates[1]}", "%Y.%d.%m")
        except Exception:
            bot.send_message(message.chat.id, "Правильно введи дату!")
            skipPeriod(message, idy)
            return
        if date_obj1 >= date_obj2:
            bot.send_message(message.chat.id, "Период представляет собой один день либо порядок неправильный!")
            skipPeriod(message, idy)
            return
        moscow_tz = ZoneInfo("Europe/Moscow")
        now_moscow = datetime.now(moscow_tz)
        today = now_moscow.replace(year=2026, hour=0, minute=0, second=0, microsecond=0)
        end_of_year = datetime(year=2026, month=12, day=31, tzinfo=moscow_tz)
        user_date1 = date_obj1.replace(year=2026, tzinfo=moscow_tz)
        user_date2 = date_obj2.replace(year=2026, tzinfo=moscow_tz)
        if not (today <= user_date1 <= end_of_year):
            bot.send_message(message.chat.id, "Дата в недопустимом диапазоне!")
            skipPeriod(message, idy)
            return
        finDate1 = date_obj1.strftime("%m-%d")
        finDate2 = date_obj2.strftime("%m-%d")

    reasonMarkup = telebot.types.ReplyKeyboardMarkup()
    for paraT in SKIP_REASONS:
        btncur = telebot.types.KeyboardButton(paraT)
        reasonMarkup.row(btncur)
    bot.send_message(message.chat.id, "Выбери причину", reply_markup=reasonMarkup)
    bot.register_next_step_handler(message, regReason3, idy, finDate1, finDate2)


def regReason3(message, idy, finDate1, finDate2):
    if message.text not in SKIP_REASONS:
        bot.send_message(message.chat.id, "Ну ты тыкни в кнопку!")
        regDate3(message, idy, finDate1, finDate2)
        return
    reason = SKIP_REASONS.index(message.text)

    start_date = datetime.strptime(f"2026-{finDate1}", "%Y-%m-%d")
    end_date = datetime.strptime(f"2026-{finDate2}", "%Y-%m-%d")
    days_diff = (end_date - start_date).days + 1

    cur = conn.cursor()
    cur.execute("SELECT id FROM skips WHERE idPerson = ? AND ? <= date AND date <= ? AND para = ?", (idy, finDate1, finDate2, 0))
    listikExisting = cur.fetchall()
    if len(listikExisting) == days_diff:
        bot.send_message(message.chat.id, "Запись про этот период уже была добавлена", reply_markup=basicMarkup)
    else:
        current_date = start_date
        while current_date <= end_date:
            finDate = current_date.strftime("%m-%d")
            dayOfWeek = current_date.weekday()
            current_date += timedelta(days=1)
            cur.execute('SELECT id FROM skips WHERE idPerson = ? AND date = ? AND reason = ? AND para = ?', (idy, finDate, 5, 0))
            ballyBack = len(cur.fetchall())
            if ballyBack != 0:
                ballyBack = -1
            else:
                cur.execute('SELECT id FROM skips WHERE idPerson = ? AND date = ? AND reason = ?', (idy, finDate, 5))
                ballyBack = len(cur.fetchall())
            cur.execute('DELETE FROM skips WHERE idPerson = ? AND date = ?', (idy, finDate))
            conn.commit()
            cur.execute('INSERT INTO skips (idPerson, date, para, reason) VALUES(?, ?, ?, ?)', (idy, finDate, 0, reason))
            conn.commit()
            if reason == 5 and dayOfWeek != 6:
                with open("timetable.json", "r", encoding="utf-8") as file:
                    timetable = json.load(file)
                daysPary = timetable[str(dayOfWeek)]
                ballyMinus = len(list(daysPary.values()))
                if ballyBack == -1:
                    ballyMinus = -1
                cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
                bally = cur.fetchall()[0][0] - (ballyMinus * 5) + (ballyBack * 5)
                cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
                conn.commit()
            elif dayOfWeek != 6:
                with open("timetable.json", "r", encoding="utf-8") as file:
                    timetable = json.load(file)
                daysPary = timetable[str(dayOfWeek)]
                ballyMinus = len(list(daysPary.values()))
                if ballyBack == -1:
                    ballyBack = ballyMinus
                cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
                bally = cur.fetchall()[0][0] + (ballyBack * 5)
                cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
                conn.commit()
        bot.send_message(message.chat.id, "Запись про период добавлена", reply_markup=basicMarkup)
        cur.close()


def statistics(message, idy):
    cur = conn.cursor()
    cur.execute("SELECT nick FROM groupmates WHERE id = ?", (idy, ))
    nicky = decrypt_value(cur.fetchall()[0][0])
    cur.close()
    if nicky in HIGH_ACCESS:
        bot.send_message(message.chat.id, "Введи дату в формате: ДД.ММ", reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, regDate4, idy)


def regDate4(message, idy):
    try:
        date_obj = datetime.strptime(f"2026.{message.text}", "%Y.%d.%m")
    except Exception:
        bot.send_message(message.chat.id, "Правильно введи дату!")
        statistics(message, idy)
        return
    moscow_tz = ZoneInfo("Europe/Moscow")
    start_of_year = datetime(year=2026, month=9, day=1, tzinfo=moscow_tz)
    end_of_year = datetime(year=2026, month=12, day=31, tzinfo=moscow_tz)
    user_date = date_obj.replace(year=2026, tzinfo=moscow_tz)
    dayOfWeek = date_obj.weekday()
    if not (start_of_year <= user_date <= end_of_year) or dayOfWeek == 6:
        bot.send_message(message.chat.id, "Дата в недопустимом диапазоне или это воскресенье!")
        statistics(message, idy)
        return
    finDate = date_obj.strftime("%m-%d")
    with open("timetable.json", "r", encoding="utf-8") as file:
        timetable = json.load(file)
    daysPary = timetable[str(dayOfWeek)]
    textStat = f"{finDate}\n"
    cur = conn.cursor()
    cur.execute("SELECT idPerson, reason FROM skips WHERE date = ? AND para = ?", (finDate, 0))
    listikPeople = cur.fetchall()
    textStat += "Весь день:\n"
    if len(listikPeople) == 0:
        textStat += "-\n"
    for i in range(len(listikPeople)):
        textStat += f"{getSurname(listikPeople[i][0])} - {SKIP_REASONS[listikPeople[i][1]]}\n"

    for klych in list(daysPary.keys()):
        textStat += daysPary[klych] + "\n"
        cur.execute("SELECT idPerson, reason FROM skips WHERE date = ? AND para = ?", (finDate, int(klych)))
        listikPeople = cur.fetchall()
        if len(listikPeople) == 0:
            textStat += "-\n"
        for i in range(len(listikPeople)):
            textStat += f"{getSurname(listikPeople[i][0])} - {SKIP_REASONS[listikPeople[i][1]]}\n"
    cur.close()
    bot.send_message(message.chat.id, textStat, reply_markup=basicMarkup)


def advertisment(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton('Перейти на Рыфмач', url="https://ryfmach.by/")
    btn2 = telebot.types.InlineKeyboardButton('Вучыць беларускую', url="https://t.me/tsiotachkabot")
    markup.add(btn1)
    markup.add(btn2)
    bot.send_message(message.chat.id, "Снизу кнопки для перехода", reply_markup=markup)
    bot.send_message(message.chat.id, "Ну давай, рассказывай, когда тебя не будет", reply_markup=basicMarkup)


def deletePeriod(message, idy):
    bot.send_message(message.chat.id, "Введи период (если один день, то 2ю дату продублировать) в формате: ДД.ММ-ДД.ММ", reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, regDate5, idy)


def regDate5(message, idy):
    listikDates = message.text.split('-')
    if len(listikDates) != 2:
        bot.send_message(message.chat.id, "Правильно введи дату!")
        deletePeriod(message, idy)
        return
    try:
        date_obj1 = datetime.strptime(f"2026.{listikDates[0]}", "%Y.%d.%m")
        date_obj2 = datetime.strptime(f"2026.{listikDates[1]}", "%Y.%d.%m")
    except Exception:
        bot.send_message(message.chat.id, "Правильно введи дату!")
        deletePeriod(message, idy)
        return
    if date_obj1 > date_obj2:
        bot.send_message(message.chat.id, "Порядок неправильный!")
        deletePeriod(message, idy)
        return
    moscow_tz = ZoneInfo("Europe/Moscow")
    now_moscow = datetime.now(moscow_tz)
    today = now_moscow.replace(year=2026, hour=0, minute=0, second=0, microsecond=0)
    end_of_year = datetime(year=2026, month=12, day=31, tzinfo=moscow_tz)
    user_date1 = date_obj1.replace(year=2026, tzinfo=moscow_tz)
    user_date2 = date_obj2.replace(year=2026, tzinfo=moscow_tz)
    if not (today < user_date1 <= end_of_year):
        bot.send_message(message.chat.id, "Дата в недопустимом диапазоне!")
        deletePeriod(message, idy)
        return
    finDate1 = date_obj1.strftime("%m-%d")
    finDate2 = date_obj2.strftime("%m-%d")

    start_date = datetime.strptime(f"2026-{finDate1}", "%Y-%m-%d")
    end_date = datetime.strptime(f"2026-{finDate2}", "%Y-%m-%d")

    cur = conn.cursor()
    current_date = start_date
    while current_date <= end_date:
        finDate = current_date.strftime("%m-%d")
        dayOfWeek = current_date.weekday()
        current_date += timedelta(days=1)
        cur.execute('SELECT id FROM skips WHERE idPerson = ? AND date = ? AND reason = ? AND para = ?', (idy, finDate, 5, 0))
        ballyBack = len(cur.fetchall())
        if ballyBack != 0:
            ballyBack = -1
        else:
            cur.execute('SELECT id FROM skips WHERE idPerson = ? AND date = ? AND reason = ?', (idy, finDate, 5))
            ballyBack = len(cur.fetchall())
        cur.execute('DELETE FROM skips WHERE idPerson = ? AND date = ?', (idy, finDate))
        conn.commit()
        if dayOfWeek != 6:
            if ballyBack == -1:
                with open("timetable.json", "r", encoding="utf-8") as file:
                    timetable = json.load(file)
                daysPary = timetable[str(dayOfWeek)]
                ballyBack = len(list(daysPary.values()))
            cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
            bally = cur.fetchall()[0][0] + (ballyBack * 5)
            cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (bally, idy))
            conn.commit()

    bot.send_message(message.chat.id, "Записи в этом периоде удалены", reply_markup=basicMarkup)
    cur.close()


def personStat(message, idy):
    cur = conn.cursor()
    cur.execute("SELECT points FROM groupmates WHERE id = ?", (idy, ))
    bally = cur.fetchall()[0][0]
    texty = f"Социальные баллы: {bally}\n"
    cur.execute("SELECT date, para FROM skips WHERE idPerson = ? ORDER BY date", (idy, ))
    listikSkipov = cur.fetchall()
    cur.close()
    texty += "Даты указаны в формате ММ-ДД\n"
    listikPar = []
    for i in range(len(listikSkipov)):
        para = str(listikSkipov[i][1])
        if para == "0":
            texty += f"{listikSkipov[i][0]}: все\n"
        else:
            listikPar.append(para)
            if i != len(listikSkipov) - 1:
                if listikSkipov[i][0] != listikSkipov[i + 1][0]:
                    texty += f"{listikSkipov[i][0]}: " + ",".join(listikPar) + '\n'
                    listikPar = []
            else:
                texty += f"{listikSkipov[i][0]}: " + ",".join(listikPar) + '\n'
                listikPar = []
    bot.send_message(message.chat.id, texty, reply_markup=basicMarkup)


def pointsAdding(message, idy):
    cur = conn.cursor()
    cur.execute("SELECT nick FROM groupmates WHERE id = ?", (idy, ))
    nicky = decrypt_value(cur.fetchall()[0][0])
    cur.close()
    if nicky in HIGH_ACCESS:
        bot.send_message(message.chat.id, "Введи сообщение в формате: баллы фамилия сообщение", reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, punish, idy)


def punish(message, idy):
    cur = conn.cursor()
    try:
        punInfo = message.text.split(" ")
        bally = int(punInfo.pop(0))
        surn = punInfo.pop(0)
        mes = " ".join(punInfo)
        cur.execute("SELECT id, name FROM groupmates")
        listikTemp = cur.fetchall()
        idishnik = -1
        for i in range(len(listikTemp)):
            if decrypt_value(listikTemp[i][1]) == surn:
                idishnik = listikTemp[i][0]
                break
        if idishnik == -1:
            raise Exception("Нет такой фамилии")
        cur.execute("SELECT id, points, userID_enc FROM groupmates WHERE id = ?", (idishnik, ))
        listikTemp = cur.fetchall()
        idyWhom = listikTemp[0][0]
        pointsCur = listikTemp[0][1]
        usId = decrypt_value(listikTemp[0][2])
        cur.execute("UPDATE groupmates SET points = ? WHERE id = ?", (pointsCur + bally, idyWhom))
        conn.commit()
        bot.send_message(usId, f"{bally} баллов: " + mes)
        bot.send_message(message.chat.id, "Успешно изменено социальное положение!", reply_markup=basicMarkup)
        cur.close()
    except Exception as e:
        bot.send_message(message.chat.id, f"Какая-то ошибка: {e}")
        cur.close()
        pointsAdding(message, idy)


def socialRating(message):
    cur = conn.cursor()
    cur.execute("SELECT name FROM groupmates ORDER BY points DESC") 
    listikStud = cur.fetchall()
    cur.close()
    texty = ""
    for i in range(len(listikStud)):
        texty += f"{i + 1}. {decrypt_value(listikStud[i][0])}\n"
    bot.send_message(message.chat.id, texty, reply_markup=basicMarkup)


def boobs(message):
    with open("image.png", "rb") as photo:
        bot.send_photo(chat_id=message.chat.id, photo=photo)
    bot.send_message(message.chat.id, "Ну давай, рассказывай, когда тебя не будет", reply_markup=basicMarkup)


bot.polling(non_stop=True)