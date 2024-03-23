import database, gpt, telebot, logging, time
from config import token, MAX_TOKENS_IN_SESSION, MAX_SESSIONS
import tokens
bot = telebot.TeleBot(token)

logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w"
)
help_message = ("Напиши /new_story, чтобы начать новую историю.\n"
                "Когда закончишь напиши /end"
                f"Обрати внимание, что у тебя всего {MAX_SESSIONS} сессий и в каждой сессии по {MAX_TOKENS_IN_SESSION} токенов")
user_info = {}
genres = ["Комедия", "Детектив", "Фантастика", "Хорор"]
characters = ["Энштейн", "Наполеон", "Нолик(из мультика про фиксиков)", "Пушкин"]
places = ["Антарктида",
          "Космический корабль",
          "Средневековый замок",
          "Непролазные джунгли"
          ]

def create_keyboard(buttons_list):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons_list)
    return keyboard

def remove_keyboard(message):
    keyboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,
                     'Удаляю клавиатуру',
                     reply_markup=keyboard)

@bot.message_handler(commands=['start'])
def start(message):
    database.create_db()
    database.create_table()
    user_id = message.from_user.id

    check = tokens.check_users() #проверка на количетво пользователей
    if check['continue']:
        logging.info("Новый пользователь")
        bot.send_message(user_id, (f"Привет {message.from_user.first_name}! Я бот, который создает истории с помощью нейросети.\n"
                                    "Мы будем писать истории поочередно. Я начну, а ты продолжишь. Чтобы понять, как это сделать нажми /help."),
                         reply_markup=create_keyboard(['/help']))
        add_new_user(user_id)
    else:
        bot.send_message(user_id, check['problems'])

def add_new_user(user_id):
    user_info[user_id] = {"genre": None, "character": None, "place": None, "added": None}

def check_user_id(user_id):
    if user_id not in user_info:
        add_new_user(user_id)


def fill(user_id):
    values = list(user_info[user_id].values())
    return not(None in values[:-1])
@bot.message_handler(commands=['help'])
def support(message):
    bot.send_message(message.from_user.id,
                     text=help_message,
                     reply_markup=create_keyboard(["/new_story"]))


@bot.message_handler(commands=['new_story'])
def new_story(message):
    user_id = message.from_user.id
    check_user_id(user_id)
    check = tokens.check_sessions(user_id) #проверка на количетво сессий у пользователя
    if check['continue']:
        if check['sessions'] > 0:
            bot.send_message(user_id, check['problems'])
        database.insert_row(user_id, 'system', gpt.SYSTEM_PROMPT, time.time(), 0, check['sessions']+1)
        bot.send_message(user_id,
                         text="Выбери жанр, в котором будет писаться история",
                         reply_markup=create_keyboard(genres))
        bot.register_next_step_handler(message, set_genre)
    else:
        bot.send_message(user_id, check['problems'])
def set_genre(message):
    user_id = message.from_user.id
    user_info[user_id]["genre"] = message.text
    bot.send_message(user_id,
                     text="Выбери персонажа, который будет главным героем в истории",
                     reply_markup=create_keyboard(characters))
    bot.register_next_step_handler(message, set_character)

def set_character(message):
    user_id = message.from_user.id
    user_info[message.from_user.id]["character"] = message.text
    bot.send_message(user_id,
                     text="Выбери место, где будет происходить история",
                     reply_markup=create_keyboard(places))
    bot.register_next_step_handler(message, set_place)

def set_place(message):
    user_id = message.from_user.id
    user_info[user_id]["place"] = message.text
    bot.send_message(user_id,
                     text=("Если хочешь, чтобы нейросеть учла еще какую-то информацию, то нажав на /add_info можешь написать ее\n"
                           "Если готов начинать, то смело жми /generate_new_story"),
                     reply_markup=create_keyboard(["/add_info", "/generate_story"]))

@bot.message_handler(commands=['add_info'])
def add_info(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     text="Введи дополнительную информацию: ")
    bot.register_next_step_handler(message, set_info)

def set_info(message):
    user_id = message.from_user.id
    if message.content_type != "text":
        bot.send_message(user_id,
                         text="Необходимо ввести текст")
        bot.register_next_step_handler(message, add_info)
    else:
        user_info[user_id]["added"] = message.text
        bot.send_message(user_id,
                         text=("Нейросеть обязательно учтет этот момент.\n"
                              "Теперь точно можно начинать придумывать историю, осталось нажать /generate_story"), reply_markup=create_keyboard(["/generate_story"]))

@bot.message_handler(commands=['generate_story'])
def generate_story(message):
    database.create_db()
    database.create_table()

    user_id = message.from_user.id
    check_user_id(user_id)
    session_id = tokens.check_sessions(user_id)['sessions']
    collection = [{
        "role": "system",
        "content": gpt.create_prompt(user_info[user_id])
    }]
    collection.extend(database.make_collection(user_id, session_id))
    check = tokens.check_tokens(user_id, session_id, collection) #проверка на количетво токенов в сессии
    if check['continue']:
        if check['problems']:
            bot.send_message(user_id, check['problems'])
        if fill(user_id):
            if check['tokens'] + 50 >= MAX_TOKENS_IN_SESSION: #токены заканчиваются
                end(message)
                return
            else:#обычный запрос
                result = gpt.ask_gpt(collection)
                logging.info("Запрос к нейросети")
            if result['done']:
                database.insert_row(user_id, 'assistant', result['text'], time.time(), result['total_tokens'], session_id)
                bot.send_message(user_id,
                                 text=result['text'] + '\n \nТеперь напиши что-нибудь ты:', reply_markup=create_keyboard(["/end"]))
                bot.register_next_step_handler(message, get_text)
            else:
                logging.error(result['error'])
                bot.send_message(user_id, 'Произошла ошибка, можешь увидеть ее в режиме /debug', reply_markup=create_keyboard(["/new_story", "/debug"]))
        else:
            bot.send_message(user_id, text = "Ты не заполнил всю информацию для начала истории. Поэтому нажми /new_story, чтобы выбрать все параметры.",
                             reply_markup=create_keyboard(["/new_story"]))
    else:
        bot.send_message(user_id, check['problems'], reply_markup=create_keyboard(["/new_story"]))


def get_text(message):
    if message.text == '/end':
        end(message)
        return
    logging.info("Получение текста от пользователя")
    user_id = message.from_user.id
    session_id = tokens.check_sessions(user_id)['sessions']
    if message.content_type != "text":
        bot.send_message(user_id,
                         text="Необходимо ввести текст")
        bot.register_next_step_handler(message, get_text)
    else:
        database.insert_row(user_id, 'user', message.text, time.time(), 0, session_id)
        generate_story(message)
@bot.message_handler(commands=['end'])
def end(message):
    logging.info("История закончилась")
    user_id = message.from_user.id
    session_id = tokens.check_sessions(user_id)['sessions']
    collection = database.make_collection(user_id, session_id)  # обычный запрос
    result = gpt.ask_gpt(collection, mode='end')
    if result['done']:
        database.insert_row(user_id, 'assistant', result['text'], time.time(), result['total_tokens'], session_id)
        bot.send_message(user_id,
                         text=result['text'])
        bot.send_message(user_id, "Спасибо, что писал со мной историю", reply_markup=create_keyboard(['/new_story', '/all_tokens']))

@bot.message_handler(commands=["debug"])
def debug(message):
    user_id = message.from_user.id
    logging.info("Режим дебаг")
    with open("log_file.txt", "rb") as f:
        bot.send_document(user_id, f)
@bot.message_handler(commands = ["all_tokens"])
def all_tokens(message):
    logging.info("Подсчет токенов")
    user_id = message.from_user.id
    sessions = tokens.check_sessions(user_id)['sessions']
    token = 0
    for session in range(1, sessions+1):
        token += tokens.check_tokens(user_id, session, [])["tokens"]
    bot.send_message(user_id, text = f"За все время использования Вы израсходовали {token} токенов")

if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.infinity_polling()