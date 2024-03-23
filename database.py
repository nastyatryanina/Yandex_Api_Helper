import sqlite3, time
from config import DB_NAME, DB_TABLE_USERS_NAME
table_name = DB_TABLE_USERS_NAME
def create_db(database_name=DB_NAME):
    db_path = f'{database_name}'
    connection = sqlite3.connect(db_path)
    connection.close()

def create_table(table_name = DB_TABLE_USERS_NAME):
    sql_query = f'CREATE TABLE IF NOT EXISTS {table_name} ' \
                f'(user_id INTEGER, ' \
                f'role TEXT, ' \
                f'content TEXT, ' \
                f'date TEXT, ' \
                f'token INTEGER,' \
                f'session_id INTEGER)'
    execute_query(sql_query)

def execute_query(sql_query, data=None, db_path=f'{DB_NAME}'):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    if data:
        cursor.execute(sql_query, data)
    else:
        cursor.execute(sql_query)

    connection.commit()
    connection.close()


def execute_selection_query(sql_query, data=None, db_path=f'{DB_NAME}'):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    if data:
        cursor.execute(sql_query, data)
    else:
        cursor.execute(sql_query)
    rows = cursor.fetchall()
    connection.close()
    return rows

def get_value_from_row(column, role, user_id):
    sql_query = f"SELECT {column} FROM {table_name} WHERE user_id = {user_id} AND role = '{role}' ORDER BY date DESC LIMIT 1"
    row = execute_selection_query(sql_query)
    return row

def get_multiple(out_column, role, search_columns, values,  user_id):
    sql_query = f"SELECT {out_column} FROM {table_name} WHERE user_id = {user_id} AND role = '{role}'"
    for i in range(len(search_columns)):
        sql_query += f" AND {search_columns[i]} = {values[i]}"
    return execute_selection_query(sql_query)

def make_collection(user_id, session_id):
    collection = []
    sql_query = f"SELECT role, content FROM {table_name} WHERE user_id = {user_id} and session_id = {session_id}"
    rows = execute_selection_query(sql_query)
    for row in rows:
        collection.append({'role': row[0], 'content': row[1]})
    return collection
def insert_row(user_id, role, content, date, tokens,  session_id):
    sql_query = "INSERT INTO user_prompts (user_id, role, content, date, token, session_id) VALUES (?, ?, ?, ?, ?, ?)"
    execute_query(sql_query, (user_id, role, content, date, tokens, session_id))


def update_row_value(user_id, column_name, new_value):
    sql_query = f"UPDATE {table_name} SET {column_name} = {new_value} WHERE user_id = {user_id}"
    execute_query(sql_query)

def select_distinct(column):
    sql_query = f"SELECT DISTINCT {column} FROM {table_name};"
    rows = execute_selection_query(sql_query)
    return rows

def show_table():
    sql_query = "SELECT * FROM user_prompts ORDER BY date DESC LIMIT 1"
    for row in execute_selection_query(sql_query):
        print(*row)
        print('')
def drop_table():
    sql_query = f"DROP TABLE {table_name}"
    execute_query(sql_query)
    print('did this')
