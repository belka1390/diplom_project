import requests
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()

class YandexGPTClient:
    """Клиент для работы с YandexGPT API (через API-ключ)"""
    
    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.model = os.getenv("YANDEX_GPT_MODEL", "yandexgpt-lite")
        
        # Проверка настроек
        if not self.api_key:
            raise ValueError("❌ YANDEX_API_KEY не установлен в .env файле!")
        if not self.folder_id:
            raise ValueError("❌ YANDEX_FOLDER_ID не установлен в .env файле!")
        
        # Проверка, что folder_id не содержит лишних частей
        if '/' in self.folder_id:
            self.folder_id = self.folder_id.split('/')[0]
            print(f"⚠️ Folder ID был исправлен: {self.folder_id}")
        
        print(f"✓ YandexGPT клиент инициализирован (API-ключ)")
        print(f"  - Folder ID: {self.folder_id}")
        print(f"  - Model: {self.model}")
        print(f"  - API Key: {self.api_key[:10]}...{self.api_key[-5:]}")
    
    def complete(self, prompt, temperature=0.3, max_tokens=2000):
        """
        Отправляет запрос в YandexGPT через API-ключ
        """
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        # ВАЖНО: Заголовки должны содержать ТОЛЬКО ASCII символы
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id
        }
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens)
            },
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт-сметчик в строительстве. Анализируй документы и извлекай структурированные данные. Отвечай ТОЛЬКО в формате JSON, без комментариев и пояснений."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            print(f"   📤 Отправка запроса в YandexGPT...")
            
            # ВАЖНО: Явно указываем кодировку UTF-8 для JSON
            json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            response = requests.post(
                url, 
                headers=headers, 
                data=json_data,  # Используем data вместо json
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"   ❌ Ошибка API: {response.status_code}")
                print(f"   Ответ: {response.text[:500]}")
                return {"error": f"API Error: {response.status_code}"}
            
            data = response.json()
            
            if "result" not in data or "alternatives" not in data["result"]:
                print(f"   ❌ Неожиданный формат ответа: {data}")
                return {"error": "Unexpected response format"}
            
            result_text = data["result"]["alternatives"][0]["message"]["text"]
            print(f"   ✓ Ответ получен ({len(result_text)} символов)")
            
            # Пытаемся распарсить JSON из ответа
            try:
                # Ищем JSON в ответе
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    parsed = json.loads(json_str)
                    print(f"   ✓ JSON успешно распарсен")
                    return parsed
            except json.JSONDecodeError as e:
                print(f"   ⚠️ Не удалось распарсить JSON: {e}")
                print(f"   Первые 200 символов ответа: {result_text[:200]}")
            
            # Если не удалось распарсить JSON, возвращаем как есть
            return {"raw_response": result_text}
            
        except requests.exceptions.Timeout:
            print("   ❌ Таймаут запроса к YandexGPT")
            return {"error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка сети: {e}")
            return {"error": str(e)}
        except UnicodeEncodeError as e:
            print(f"   ❌ Ошибка кодировки: {e}")
            print(f"   Проверьте, что все строки в UTF-8")
            return {"error": f"Encoding error: {e}"}
    
    def extract_construction_data(self, document_text, document_type="unknown"):
        """
        Извлекает структурированные данные из текста строительного документа
        """
        # Очищаем текст от возможных проблемных символов
        document_text = document_text.encode('utf-8', errors='ignore').decode('utf-8')
        
        prompt = f"""
Проанализируй следующий текст строительного документа и извлеки структурированные данные.
Тип документа: {document_type}

ТРЕБОВАНИЯ К ИЗВЛЕЧЕНИЮ:
1. Объемы работ (площадь фасада в кв.м, длина в п.м, объем в куб.м и т.д.)
2. Типы работ (утепление, покраска, штукатурка, вентфасад, кровля и т.д.)
3. Материалы (названия, марки, количество)
4. Этажность здания
5. Сроки выполнения работ (в днях или датах)
6. Стоимость работ (если указана)
7. Регион/адрес объекта
8. Требования к квалификации подрядчика

ФОРМАТ ОТВЕТА (строго JSON, без комментариев):
{{
    "work_volumes": {{
        "facade_area_m2": число или null,
        "roof_area_m2": число или null,
        "length_m": число или null,
        "volume_m3": число или null,
        "other": "описание других объемов"
    }},
    "work_types": ["список", "типов", "работ"],
    "materials": [
        {{"name": "название", "unit": "ед.изм", "quantity": число}}
    ],
    "building_info": {{
        "floors": число или null,
        "address": "адрес",
        "region": "регион"
    }},
    "duration_days": число или null,
    "cost_rub": число или null,
    "contractor_requirements": ["требования", "к", "подрядчику"],
    "additional_info": "любая дополнительная важная информация"
}}

ТЕКСТ ДОКУМЕНТА:
{document_text[:8000]}
"""
        
        return self.complete(prompt, temperature=0.2, max_tokens=3000)