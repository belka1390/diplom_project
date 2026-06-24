diplom_project/
├── src/
│   ├── parser/              # Парсинг ЕИС
│   ├── processor/           # Обработка документов (YandexGPT)
│   ├── ml/                  # 🆕 ML-модели
│   │   ├── training.py      # Обучение CatBoost
│   │   ├── explainability.py # SHAP-анализ
│   │   └── predictor.py     # Прогнозирование
│   └── config.py
├── notebooks/
│   └── vkr_1.ipynb          # 🆕 Ваш исследовательский notebook
├── models/                  # 🆕 Обученные модели
├── tests/
├── data/
├── reports/                 # SHAP-отчеты
├── docs/
├── .env
└── main.py