# Добавьте в main.py новые команды

def run_train():
    """Обучение ML-моделей"""
    from src.ml import ModelTrainer
    import pandas as pd
    from sklearn.model_selection import train_test_split
    
    print("=== Обучение ML-моделей ===")
    
    # Загрузка данных (пример)
    # TODO: Замените на реальный путь к вашим данным
    data_path = Config.DATA_PROCESSED_DIR / "ml_ready_data.csv"
    
    if not data_path.exists():
        print(f"❌ Файл {data_path} не найден.")
        print("Сначала выполните этап обработки документов и подготовки данных.")
        return
    
    df = pd.read_csv(data_path)
    
    # Разделение на признаки и целевые переменные
    # TODO: Настройте под ваши данные
    X = df.drop(['duration_days', 'cost_rub'], axis=1)
    y_duration = df['duration_days']
    y_cost = df['cost_rub']
    
    # Time Series Split (для временных данных)
    tscv = TimeSeriesSplit(n_splits=5)
    
    # Берем последнее разбиение для финального обучения
    for train_idx, test_idx in tscv.split(X):
        pass  # Берем последнее разбиение
    
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_duration_train, y_duration_test = y_duration.iloc[train_idx], y_duration.iloc[test_idx]
    y_cost_train, y_cost_test = y_cost.iloc[train_idx], y_cost.iloc[test_idx]
    
    # Обучение
    trainer = ModelTrainer()
    results = trainer.train(
        X_train, y_duration_train, y_cost_train,
        X_test, y_duration_test, y_cost_test
    )
    
    print("\n✓ Обучение завершено!")
    print(f"Модели сохранены в: {trainer.models_dir}")


def run_explain():
    """SHAP-анализ обученных моделей"""
    from src.ml import ModelTrainer, SHAPExplainer
    import pandas as pd
    
    print("=== SHAP-анализ моделей ===")
    
    # Загрузка данных
    data_path = Config.DATA_PROCESSED_DIR / "ml_ready_data.csv"
    if not data_path.exists():
        print(f"❌ Файл {data_path} не найден.")
        return
    
    df = pd.read_csv(data_path)
    X = df.drop(['duration_days', 'cost_rub'], axis=1)
    
    # Загрузка моделей
    trainer = ModelTrainer()
    trainer.load_models()
    
    # SHAP-анализ для сроков
    print("\n📊 Анализ модели СРОКОВ...")
    explainer_duration = SHAPExplainer(trainer.model_duration)
    
    reports_dir = Config.REPORTS_DIR
    reports_dir.mkdir(exist_ok=True)
    
    explainer_duration.plot_summary(
        X.head(100), 
        save_path=reports_dir / "shap_summary_duration.png"
    )
    
    importance_duration = explainer_duration.get_feature_importance(X.head(100))
    importance_duration.to_csv(reports_dir / "feature_importance_duration.csv", index=False)
    print(f"✓ Важность признаков сохранена: {reports_dir / 'feature_importance_duration.csv'}")
    
    # SHAP-анализ для стоимости
    print("\n💰 Анализ модели СТОИМОСТИ...")
    explainer_cost = SHAPExplainer(trainer.model_cost)
    
    explainer_cost.plot_summary(
        X.head(100), 
        save_path=reports_dir / "shap_summary_cost.png"
    )
    
    importance_cost = explainer_cost.get_feature_importance(X.head(100))
    importance_cost.to_csv(reports_dir / "feature_importance_cost.csv", index=False)
    print(f"✓ Важность признаков сохранена: {reports_dir / 'feature_importance_cost.csv'}")
    
    print("\n✓ SHAP-анализ завершен!")
    print(f"Отчеты сохранены в: {reports_dir}")


# Обновите функцию main()
def main():
    parser = argparse.ArgumentParser(
        description="Система анализа закупок в строительстве"
    )
    parser.add_argument(
        'command',
        choices=['parse', 'process', 'test-yandex', 'train', 'explain', 'all'],
        help='Команда для выполнения'
    )
    
    args = parser.parse_args()
    
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    
    if args.command == 'parse':
        run_parser()
    elif args.command == 'process':
        run_processor()
    elif args.command == 'test-yandex':
        run_test_yandex()
    elif args.command == 'train':
        run_train()
    elif args.command == 'explain':
        run_explain()
    elif args.command == 'all':
        print("=== Запуск полного цикла ===")
        run_parser()
        run_processor()
        run_train()
        run_explain()
        print("=== Полный цикл завершен ===")