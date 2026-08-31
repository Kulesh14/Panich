import telebot
from telebot import types


basicMarkup = types.ReplyKeyboardMarkup()
btn01 = types.KeyboardButton('Пропуск пары')
btn02 = types.KeyboardButton('Пропуск дня')
btn03 = types.KeyboardButton('Пропуск периода')
btn04 = types.KeyboardButton('Статистика')
btn05 = types.KeyboardButton('Реклама')
basicMarkup.row(btn01)
basicMarkup.row(btn02)
basicMarkup.row(btn03)
basicMarkup.row(btn04, btn05)