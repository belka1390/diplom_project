import os
import requests
import json
from src.processor.yandex_gpt_client import YandexGPTClient

os.getenv (API_KEY) 
os.getenv (FOLDER_ID)

# Шаг 1: Получаем IAM-токен из API-ключа
iam_url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
r = requests.post(iam_url, json={'yandexPassportOauthToken': API_KEY})
if r.status_code != 200:
    raise Exception(f"Не удалось получить IAM-токен: {r.text}")

iam_token = r.json()['iamToken']
print("IAM-токен получен.")

# Шаг 2: Инициализируем клиент с токеном (проверь название аргумента в документации своей версии!)
# Часто это token, iam_token или oauth_token
try:
    client = YandexGPTClient(
        token=iam_token,          # Попробуй этот вариант
        folder_id=FOLDER_ID
        # ИЛИ попробуй: iam_token=iam_token
        # ИЛИ попробуй: oauth_token=iam_token
    )
    
    print("Клиент создан, отправляем запрос...")
    result = client.complete("Привет!", max_tokens=10)
    print(result)
except TypeError as e:
    print(f"Ошибка инициализации: {e}")
    print("Попробуй изменить имя аргумента (token / iam_token / oauth_token).")
