import requests, logging, time, sys, tokens
from config import MAX_TOKENS_IN_SESSION
sys.path.insert(1, 'C:\\Users\\Admin\\Desktop\\Яндекс-практикум\\secret_info')
from Yandex_Api_Gpt import folder_id
expires_at  = time.time()
iam_token = ''
SYSTEM_PROMPT = (
    "Ты пишешь историю вместе с человеком. "
    "Историю вы пишете по очереди. Начинает человек, а ты продолжаешь. "
    "Если это уместно, ты можешь добавлять в историю диалог между персонажами. "
    "Диалоги пиши с новой строки и отделяй тире. "
    "Не пиши никакого пояснительного текста в начале, а просто логично продолжай историю."
)
CONTINUE_STORY = 'Продолжи сюжет в 1-3 предложения и оставь интригу. Не пиши никакой пояснительный текст от себя'
END_STORY = 'Напиши завершение истории c неожиданной развязкой. Не пиши никакой пояснительный текст от себя'
def create_prompt(user_data):
    prompt = (f"\nНапиши начало истории в стиле {user_data['genre']} "
              f"с главным героем {user_data['character']}. "
              f"Вот начальный сеттинг: \n{user_data['place']}. \n"
              "Начало должно быть коротким, 1-3 предложения.\n")

    if user_data['added'] != None:
        prompt += (f"Также пользователь попросил учесть "
                   f"следующую дополнительную информацию: {user_data['added']} ")

    prompt += 'Не пиши никакие подсказки пользователю, что делать дальше. Он сам знает'
    return prompt


def ask_gpt(collection, mode='continue'):
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    check_iam_token()
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }

    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 50
        },
        "messages": []
    }

    for row in collection:
        content = row['content']
        data["messages"].append({
            "role": row["role"],
            "text": content
        })
    if mode == 'end':
        data["messages"][-1]['text'] += '\n' + END_STORY
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            result = {"done": False,
                      "error": f"error: {response.status_code}"}
            return result
        print(f'input_tokens: {response.json()["result"]["usage"]["inputTextTokens"]}')
        result = {"done": True,
                  "text": response.json()['result']['alternatives'][0]['message']['text'],
                  "total_tokens": int(response.json()["result"]["usage"]["totalTokens"])}


    except Exception as e:
        result = {"done": False,
                  "error": f"Возникла непредвиденная ошибка."}
    return result

def create_new_token():
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    return response.json()

def check_iam_token():
    global expires_at, iam_token
    if expires_at > time.time()+10:
        new_token = create_new_token()
        iam_token = new_token['access_token']
        expires_at = new_token['expires_in'] + time.time()
