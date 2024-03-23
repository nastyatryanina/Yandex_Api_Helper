import database, requests, sys
from config import MAX_TOKENS_IN_SESSION, MAX_USERS, MAX_SESSIONS
sys.path.insert(1, 'C:\\Users\\Admin\\Desktop\\Яндекс-практикум\\secret_info')
from Yandex_Api_Gpt import iam_token, folder_id
def check_sessions(user_id):
    used_sources = database.get_value_from_row('session_id', 'system', user_id)
    if used_sources:
        sessions = used_sources[0][0]
        print(f'sessions: {sessions}')
        if sessions >= MAX_SESSIONS:
            return {'continue': False, 'problems': 'Вы израсходовали все сессии. Спасибо, что использовали нашего бота!', 'sessions': sessions}

        return {'continue': True, 'problems': f'У Вас осталось {MAX_SESSIONS - sessions} сессий.', 'sessions': sessions}

    return {'continue': True, 'problems': '', 'sessions': 0}
def check_tokens(user_id, session_id, collection):
    used_sources = database.get_multiple('token', 'assistant', ['session_id'], [session_id], user_id)
    tokens_of_session = count_tokens_in_dialog(collection)
    print(f"tokens_in_collection: {tokens_of_session}")
    if used_sources:
        for i in used_sources:
            tokens_of_session += int(i[0])
    print(f"tokens: {tokens_of_session}")
    if tokens_of_session >= MAX_TOKENS_IN_SESSION:
        return {'continue': False,
                'problems': 'Вы израсходовали все токены в этой сессии. Вы можете начать новую, введя /new_story.',
                'tokens': tokens_of_session}

    if tokens_of_session + 50 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше 50 токенов
        return {'continue': True,
                'problems': f'Вы приближаетесь к лимиту в {MAX_TOKENS_IN_SESSION} токенов в этой сессии. Ваш запрос содержит суммарно {tokens_of_session} токенов.',
                'tokens': tokens_of_session}

    if tokens_of_session / 2 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше половины
        return {'continue': True,
                'problems': f'Вы использовали больше половины токенов в этой сессии. Ваш запрос содержит суммарно {tokens_of_session} токенов.',
                'tokens': tokens_of_session}

    return {'continue': True, 'problems': '', 'tokens': tokens_of_session}


def check_users():
    total_users = len(database.select_distinct('user_id'))
    if total_users >= MAX_USERS:
        return {'continue': False, 'problems': "Эх, к сожалению, Вы не можете воспользоваться нашим ботом, так как лимит пользователей уже исчерпан."}

    return {'continue': True, 'problems': ''}


def count_tokens_in_dialog(collection):
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
       "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
       "maxTokens": 100,
       "messages": []
    }
    for row in collection:
        data["messages"].append(
            {
                "role": row["role"],
                "text": row["content"]
            }
        )

    return len(
        requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion",
            json=data,
            headers=headers
        ).json()["tokens"]
    )
