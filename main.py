import sqlite3
import pandas as pd
from sus import get_id_hash, encrypt_value, decrypt_value


def addingGroupmate(name, sur, nick):
    conn = sqlite3.connect('group.db')
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
    conn.close()


def createTable():
    df = pd.read_csv('groupmates.csv', sep=';', encoding='utf-8', header=None)
    for i in range(len(df)):
        addingGroupmate(df.iloc[i, 0], df.iloc[i, 1], df.iloc[i, 2])