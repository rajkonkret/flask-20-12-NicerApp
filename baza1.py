import sqlite3
sql_connection = None
try:
    sql_connection = sqlite3.connect('data/cantor.db')
    query = '''create table transactions(id integer primary key autoincrement,
    currency varchar(5),
    amount int,
    user varchar(5),
    trans_date date not null default(date()));'''
    cursor = sql_connection.cursor()

    cursor.execute(query)
    sql_connection.commit()
except sqlite3.Error as e:
    print("Bład", e)
finally:
    if sql_connection:
        sql_connection.close()
