import telebot
from telebot import types


basicMarkup = types.ReplyKeyboardMarkup()
btn01 = types.KeyboardButton('Пропуск пары')
btn02 = types.KeyboardButton('Пропуск дня')
btn03 = types.KeyboardButton('Пропуск периода')
btn04 = types.KeyboardButton('Статистика')
btn05 = types.KeyboardButton('Реклама')
btn06 = types.KeyboardButton('Отменить')
btn07 = types.KeyboardButton('Личная статистика')
basicMarkup.row(btn01)
basicMarkup.row(btn02)
basicMarkup.row(btn03)
basicMarkup.row(btn06, btn07)
basicMarkup.row(btn04, btn05)

hide_keyboard = types.ReplyKeyboardRemove()