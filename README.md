# Связь с гитом
### https://github.com/belka1390/diplom-project

git init
git add .
git commit -m "first commit"
git branch -M master
git remote add origin https://github.com/belka1390/diplom-project.git
git push -u origin master

# parsing.py

### Программа для сбора данных грязных данных с Госзакупок.
Команды запуска:
- python -m venv venv
- venv\Scripts\activate
- pip install -r requirements.txt
- python.exe -m pip install --upgrade pip
- python parsing.py

### Настройка .env по поиску
URL поиска с уже настроенными фильтрами: SEARCH_URL=""
Имя выходного CSV-файла с метаданными: CSV_FILENAME=""
Папка для скачанных документов: DOCS_DIR=""
Сколько страниц результатов парсить (максимум): MAX_PAGES=
МАКСИМАЛЬНОЕ КОЛИЧЕСТВО ЗАКУПОК ДЛЯ ОБРАБОТКИ: MAX_TENDERS=
Режим браузера: False - видно окно (для отладки), True - скрытый режим: HEADLESS=