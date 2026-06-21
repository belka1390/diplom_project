import os
import re
import time
import queue
import threading
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# 1. ЗАГРУЗКА НАСТРОЕК ИЗ .env
# ============================================================
load_dotenv()
SEARCH_URL = os.getenv("SEARCH_URL")
CSV_FILENAME = os.getenv("CSV_FILENAME", "tenders_data.csv")
DOCS_DIR = os.getenv("DOCS_DIR", "downloaded_docs")
MAX_PAGES = int(os.getenv("MAX_PAGES", 3))
MAX_TENDERS = int(os.getenv("MAX_TENDERS", 5))
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

# Очередь для передачи задач между потоками
task_queue = queue.Queue()

# Флаг остановки потока скачивания
stop_downloading = threading.Event()

# Счетчик обработанных закупок
processed_count = 0
count_lock = threading.Lock()


# ============================================================
# 2. ИНИЦИАЛИЗАЦИЯ БРАУЗЕРА
# ============================================================
def init_driver():
    """Инициализация защищенного Chrome драйвера"""
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    
    driver = uc.Chrome(options=options, version_main=149)
    driver.implicitly_wait(10)
    return driver


# ============================================================
# 3. ОПРЕДЕЛЕНИЕ РЕАЛЬНОГО ТИПА ФАЙЛА ПО СИГНАТУРЕ
# ============================================================
def detect_real_extension(file_path):
    """Определяет реальный тип файла по первым байтам (magic bytes)."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            if not header:
                return None
            
            if header.startswith(b'%PDF'):
                return '.pdf'
            if header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06'):
                lower_path = file_path.lower()
                if lower_path.endswith('.docx'): return '.docx'
                elif lower_path.endswith('.xlsx'): return '.xlsx'
                elif lower_path.endswith('.pptx'): return '.pptx'
                elif lower_path.endswith('.odt'): return '.odt'
                else: return '.zip'
            if header.startswith(b'Rar!\x1a\x07'):
                return '.rar'
            if header.startswith(b"7z\xbc\xaf'\x1c"):
                return '.7z'
            if header.startswith(b'\xd0\xcf\x11\xe0'):
                return '.xls'
            if header.startswith(b'\xdb\xa5\x2d\x00'):
                return '.doc'
            
            try:
                text_sample = header.decode('utf-8', errors='ignore')
                if ',' in text_sample or ';' in text_sample or '<?xml' in text_sample.lower():
                    if '.csv' in file_path.lower(): return '.csv'
                    elif '.xml' in file_path.lower(): return '.xml'
                    else: return '.txt'
            except:
                pass
            return None
    except Exception as e:
        print(f"      -> Ошибка определения типа файла: {e}")
        return None


# ============================================================
# 4. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: ПРОКРУТКА СТРАНИЦЫ
# ============================================================
def scroll_page(driver):
    """Прокручивает страницу вниз для загрузки ленивых элементов"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):  # Делаем 3 прокрутки
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    # Прокрутка обратно наверх
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


# ============================================================
# 5. ПОТОК 1: ПАРСИНГ МЕТАДАННЫХ
# ============================================================
def parse_search_page(driver):
    """Парсит карточки закупок, пишет в CSV и ставит задачи в очередь"""
    global processed_count
    
    print("[Поток 1] Запуск парсера метаданных...")
    print(f"[Поток 1] Лимит закупок для обработки: {MAX_TENDERS}")
    
    driver.get(SEARCH_URL)
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-registry-entry-block"))
        )
        print("[Поток 1] Страница с результатами загружена.")
    except Exception as e:
        print(f"[Поток 1] Ошибка загрузки результатов. Возможно, капча или нет закупок: {e}")
        stop_downloading.set()
        return

    # Создаем CSV с заголовками
    df = pd.DataFrame(columns=[
        'regNumber', 'status', 'object_name', 'customer', 'price', 
        'date_published', 'date_updated', 'date_deadline', 'docs_url'
    ])
    df.to_csv(CSV_FILENAME, index=False, encoding='utf-8-sig')

    for page_num in range(1, MAX_PAGES + 1):
        with count_lock:
            if processed_count >= MAX_TENDERS:
                print(f"[Поток 1] Достигнут лимит закупок ({MAX_TENDERS}). Завершаем парсинг.")
                stop_downloading.set()
                break
        
        print(f"[Поток 1] Парсинг страницы {page_num}...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.find_all('div', class_='search-registry-entry-block')
        
        if not cards:
            print("[Поток 1] Карточки не найдены. Завершаем.")
            break

        for card in cards:
            with count_lock:
                if processed_count >= MAX_TENDERS:
                    print(f"[Поток 1] Достигнут лимит закупок ({MAX_TENDERS}). Останавливаемся.")
                    stop_downloading.set()
                    break
            
            try:
                # Номер закупки (ID)
                reg_num_tag = card.find('div', class_='registry-entry__header-mid__number').find('a')
                reg_number = reg_num_tag.text.strip().replace('№', '').strip()
                
                # === ФОРМИРОВАНИЕ URL СТРАНИЦЫ ДОКУМЕНТОВ ===
                docs_url = None
                
                # Способ 1: Ищем ссылку на карточку закупки (common-info.html)
                reg_num_div = card.find('div', class_='registry-entry__header-mid__number')
                card_link = reg_num_div.find('a', href=True) if reg_num_div else None
                
                if card_link:
                    card_url = card_link['href']
                    
                    # Проверяем, это 223-ФЗ или 44-ФЗ
                    if '/notice223/' in card_url or 'purchaseNoticeNumber' in card_url:
                        # 223-ФЗ
                        docs_url = f"https://zakupki.gov.ru/epz/order/notice/notice223/documents.html?purchaseNoticeNumber={reg_number}"
                    else:
                        # 44-ФЗ - извлекаем тип процедуры из URL карточки
                        match = re.search(r'/notice/(\w+)/view/', card_url)
                        if match:
                            procedure_type = match.group(1)
                            docs_url = f"https://zakupki.gov.ru/epz/order/notice/{procedure_type}/view/documents.html?regNumber={reg_number}"
                
                # Способ 2: Если не удалось сформировать URL, ищем ссылку "Документы" в карточке
                if not docs_url:
                    # Ищем все ссылки с текстом "Документы" или href содержащим "documents.html"
                    all_links = card.find_all('a', href=True)
                    for link in all_links:
                        link_text = link.get_text(strip=True).lower()
                        link_href = link['href'].lower()
                        
                        if 'документы' in link_text or 'documents.html' in link_href:
                            docs_url = link['href']
                            if not docs_url.startswith('http'):
                                docs_url = "https://zakupki.gov.ru" + docs_url
                            break
                
                # Способ 3: Если всё ещё нет URL, используем универсальный формат для 44-ФЗ
                if not docs_url:
                    # По умолчанию предполагаем электронный аукцион (ea20)
                    docs_url = f"https://zakupki.gov.ru/epz/order/notice/ea20/view/documents.html?regNumber={reg_number}"
                    print(f"   -> ⚠️ Использован универсальный URL для {reg_number}")
                
                # Остальной код без изменений
                status_tag = card.find('div', class_='registry-entry__header-mid__title')
                status = status_tag.get_text(strip=True) if status_tag else "Неизвестно"

                obj_tags = card.find_all('div', class_='registry-entry__body-value')
                object_name = obj_tags[0].get_text(strip=True) if obj_tags else ""

                cust_tag = card.find('div', class_='registry-entry__body-href')
                customer = cust_tag.get_text(strip=True) if cust_tag else ""

                price_tag = card.find('div', class_='price-block__value')
                price = price_tag.get_text(strip=True) if price_tag else "0"

                dates = {}
                date_titles = card.find_all('div', class_='data-block__title')
                for title in date_titles:
                    title_text = title.get_text(strip=True)
                    value_tag = title.find_next('div', class_='data-block__value')
                    if value_tag:
                        dates[title_text] = value_tag.get_text(strip=True)

                new_row = {
                    'regNumber': reg_number,
                    'status': status,
                    'object_name': object_name,
                    'customer': customer,
                    'price': price,
                    'date_published': dates.get('Размещено', ''),
                    'date_updated': dates.get('Обновлено', ''),
                    'date_deadline': dates.get('Окончание подачи заявок', ''),
                    'docs_url': docs_url
                }
                pd.DataFrame([new_row]).to_csv(CSV_FILENAME, mode='a', header=False, index=False, encoding='utf-8-sig')

                with count_lock:
                    processed_count += 1
                    current_count = processed_count
                
                print(f"   -> Обработано закупок: {current_count}/{MAX_TENDERS}")
                print(f"      URL документов: {docs_url}")

                if docs_url:
                    task_queue.put((reg_number, docs_url))

                time.sleep(1)

            except Exception as e:
                print(f"   -> Ошибка парсинга карточки: {e}")
                continue
        
        with count_lock:
            if processed_count >= MAX_TENDERS:
                break

        if page_num < MAX_PAGES:
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'pagination')]/li[not(@class='active')][last()]/a"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", next_btn)
                print("[Поток 1] Переход на следующую страницу...")
                time.sleep(7)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "search-registry-entry-block"))
                )
            except Exception:
                print("[Поток 1] Кнопка 'Следующая страница' не найдена. Завершаем.")
                break

    print("[Поток 1] Парсинг завершен.")
    stop_downloading.set()

# ============================================================
# 6. ПОТОК 2: СКАЧИВАНИЕ ДОКУМЕНТОВ (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ============================================================
def download_documents():
    """Скачивает документы в папки по ID закупки (финальная стабильная версия)"""
    print("[Поток 2] Запуск загрузчика документов...")
    
    def create_driver():
        """Создает новый экземпляр драйвера"""
        return init_driver()
    
    driver_dl = create_driver()
    session = requests.Session()
    
    os.makedirs(DOCS_DIR, exist_ok=True)
    restart_count = 0

    while not stop_downloading.is_set() or not task_queue.empty():
        try:
            reg_number, docs_url = task_queue.get(timeout=2)
        except queue.Empty:
            continue

        print(f"[Поток 2] Обработка закупки {reg_number}...")
        folder_path = os.path.join(DOCS_DIR, reg_number)
        os.makedirs(folder_path, exist_ok=True)

        # === ПРОВЕРКА ЖИЗНЕСПОСОБНОСТИ БРАУЗЕРА ПЕРЕД ОТКРЫТИЕМ ===
        try:
            _ = driver_dl.current_url
        except Exception:
            print(f"   -> Браузер мёртв! Перезапускаю...")
            try:
                driver_dl.quit()
            except:
                pass
            driver_dl = create_driver()
            restart_count += 1
            if restart_count > 5:
                print(f"   -> КРИТИЧЕСКАЯ ОШИБКА: браузер падал {restart_count} раз. Прерываю.")
                break

        try:
            driver_dl.get(docs_url)
            print(f"   -> Страница открыта, ждём загрузки (12 сек)...")
            time.sleep(12)  # Увеличил до 12 секунд для полной загрузки

            # === ПРОВЕРКА НА КАПЧУ ===
            page_text = driver_dl.page_source.lower()
            if 'подтвердите, что вы не робот' in page_text or 'captcha' in page_text:
                print(f"   -> ⚠️ ОБНАРУЖЕНА КАПЧА! Жду 30 секунд, чтобы вы решили её вручную в окне браузера...")
                time.sleep(30)
                # После решения капчи страница должна перезагрузиться автоматически
                time.sleep(5)

            # Переносим cookies из Selenium в requests
            for cookie in driver_dl.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            
            session.headers.update({
                'User-Agent': driver_dl.execute_script("return navigator.userAgent;"),
                'Referer': docs_url
            })

            soup_dl = BeautifulSoup(driver_dl.page_source, 'html.parser')
            
            # === СОХРАНЕНИЕ HTML ДЛЯ ОТЛАДКИ ===
            debug_html_path = os.path.join(folder_path, "_debug_page.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(driver_dl.page_source)
            
            # === ПОИСК ВСЕХ ССЫЛОК НА ФАЙЛЫ ===
            all_links = soup_dl.find_all('a', href=True)
            
            file_links = []
            for link in all_links:
                href = link['href']
                
                if any(pattern in href.lower() for pattern in [
                    'file.html', 'download', '/filestore/'
                ]):
                    if any(exclude in href.lower() for exclude in [
                        'signview', 'printform', 'listmodal', 'printview', 'rss'
                    ]):
                        continue
                    
                    file_links.append(link)
            
            if not file_links:
                print(f"   -> ⚠️ Файлы не найдены на странице {reg_number}.")
                print(f"   -> Проверите файл: {debug_html_path}")
                
                # === ПОВТОРНАЯ ПОПЫТКА через 5 секунд ===
                print(f"   -> Пробую ещё раз через 5 секунд...")
                time.sleep(5)
                driver_dl.get(docs_url)
                time.sleep(10)
                
                soup_dl = BeautifulSoup(driver_dl.page_source, 'html.parser')
                all_links = soup_dl.find_all('a', href=True)
                
                file_links = []
                for link in all_links:
                    href = link['href']
                    if any(pattern in href.lower() for pattern in [
                        'file.html', 'download', '/filestore/'
                    ]):
                        if any(exclude in href.lower() for exclude in [
                            'signview', 'printform', 'listmodal', 'printview', 'rss'
                        ]):
                            continue
                        file_links.append(link)
                
                if not file_links:
                    print(f"   -> ❌ Файлы всё ещё не найдены. Пропускаю закупку.")
                    task_queue.task_done()
                    continue
                else:
                    print(f"   -> ✅ Повторная попытка успешна! Найдено {len(file_links)} файлов.")
            
            print(f"   -> Найдено {len(file_links)} ссылок на файлы.")

            downloaded_count = 0
            
            for file_link in file_links:
                try:
                    href = file_link['href']
                    
                    # === ИЗВЛЕЧЕНИЕ ИМЕНИ ФАЙЛА ===
                    file_name = None
                    
                    if file_link.get('title'):
                        file_name = file_link.get('title', '').strip()
                    
                    if not file_name and file_link.get('data-tooltip'):
                        tooltip = file_link.get('data-tooltip', '')
                        if '<' in tooltip:
                            tooltip_soup = BeautifulSoup(tooltip, 'html.parser')
                            file_name = tooltip_soup.get_text(strip=True)
                        else:
                            file_name = tooltip.strip()
                    
                    if not file_name:
                        file_name = file_link.get_text(strip=True)
                        
                        parent = file_link.parent
                        img = parent.find('img', alt=True) if parent else None
                        if not img:
                            img = file_link.find_previous('img', alt=True)
                        
                        if img and '.' not in file_name:
                            alt_text = img['alt'].lower()
                            if 'word' in alt_text or 'docx' in alt_text:
                                file_name += '.docx'
                            elif 'excel' in alt_text or 'xls' in alt_text:
                                file_name += '.xlsx'
                            elif 'pdf' in alt_text or 'acrobat' in alt_text:
                                file_name += '.pdf'
                            elif 'rar' in alt_text or 'zip' in alt_text or 'архив' in alt_text:
                                file_name += '.rar'
                            elif 'csv' in alt_text:
                                file_name += '.csv'
                            elif 'txt' in alt_text or 'текст' in alt_text:
                                file_name += '.txt'
                            else:
                                file_name += '.bin'
                    
                    if not file_name or len(file_name) < 2:
                        continue
                    
                    file_name = re.sub(r'[\\/*?:"<>|]', "_", file_name)
                    if len(file_name) > 150:
                        name_part, ext_part = os.path.splitext(file_name)
                        file_name = name_part[:145] + ext_part
                    
                    if not href.startswith('http'):
                        href = "https://zakupki.gov.ru" + href
                    
                    file_path = os.path.join(folder_path, file_name)
                    
                    # === СКАЧИВАНИЕ ФАЙЛА ===
                    response = session.get(href, stream=True, timeout=60)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type and 'file.html' not in href:
                            print(f"      -> Пропуск {file_name}: сервер вернул HTML")
                            continue
                        
                        with open(file_path, 'wb') as f:
                            for chunk in response.iter_content(8192):
                                f.write(chunk)
                        
                        real_ext = detect_real_extension(file_path)
                        if real_ext:
                            current_ext = os.path.splitext(file_path)[1].lower()
                            if current_ext != real_ext:
                                new_file_path = os.path.splitext(file_path)[0] + real_ext
                                os.rename(file_path, new_file_path)
                                print(f"      ✓ Скачан и исправлен: {file_name} -> {os.path.basename(new_file_path)}")
                            else:
                                print(f"      ✓ Скачан: {file_name}")
                        else:
                            print(f"      ✓ Скачан (тип не определен): {file_name}")
                        
                        downloaded_count += 1
                    else:
                        print(f"      ✗ Ошибка HTTP {response.status_code} для {file_name}")
                    
                    time.sleep(3)
                    
                except Exception as file_err:
                    print(f"      -> Ошибка при обработке файла: {file_err}")
                    continue
            
            print(f"   -> Итого скачано {downloaded_count} файлов в папку {reg_number}")
            task_queue.task_done()
            
            # Увеличенная пауза между закупками (10 секунд)
            time.sleep(10)

        except Exception as e:
            print(f"   -> Критическая ошибка при обработке {reg_number}: {e}")
            
            # === ПРОВЕРКА И ПЕРЕЗАПУСК БРАУЗЕРА ПОСЛЕ ОШИБКИ ===
            try:
                _ = driver_dl.current_url
            except Exception:
                print(f"   -> 💥 Браузер упал! Перезапускаю...")
                try:
                    driver_dl.quit()
                except:
                    pass
                driver_dl = create_driver()
                restart_count += 1
                print(f"   -> Новый браузер запущен. Счетчик перезапусков: {restart_count}")
                
                if restart_count > 5:
                    print(f"   -> ❌ Слишком много перезапусков. Прерываю работу.")
                    task_queue.task_done()
                    break
            
            task_queue.task_done()

    print("[Поток 2] Работа завершена.")
    try:
        driver_dl.quit()
    except Exception:
        pass


# ============================================================
# 7. ТОЧКА ВХОДА
# ============================================================
if __name__ == "__main__":
    print("=== Инициализация системы сбора данных ===")
    print(f"URL поиска: {SEARCH_URL[:80]}...")
    print(f"Страниц для парсинга (макс): {MAX_PAGES}")
    print(f"Лимит закупок для обработки: {MAX_TENDERS}")
    print(f"Папка для документов: {DOCS_DIR}")
    print(f"CSV файл: {CSV_FILENAME}")
    print("=" * 50)
    
    driver_main = init_driver()

    thread_parser = threading.Thread(target=parse_search_page, args=(driver_main,))
    thread_downloader = threading.Thread(target=download_documents)

    thread_downloader.start()
    thread_parser.start()

    thread_parser.join()
    thread_downloader.join()
    
    # Безопасное закрытие драйвера
    try:
        driver_main.quit()
    except Exception:
        pass  # Игнорируем ошибки при закрытии
    
    print("=" * 50)
    print("=== Сбор данных полностью завершен ===")
    print(f"Обработано закупок: {processed_count}")
    print(f"Метаданные сохранены в: {os.path.abspath(CSV_FILENAME)}")
    print(f"Документы сохранены в: {os.path.abspath(DOCS_DIR)}")