"""
Модуль обучения ML-моделей для прогнозирования сроков и стоимости.
"""
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from pathlib import Path

from src.config import Config


class ModelTrainer:
    """Обучение моделей CatBoost для прогнозирования"""
    
    def __init__(self):
        self.model_duration = None
        self.model_cost = None
        self.models_dir = Config.PROJECT_ROOT / "models"
        self.models_dir.mkdir(exist_ok=True)
    
    def train(self, X_train, y_duration_train, y_cost_train, 
              X_test, y_duration_test, y_cost_test):
        """
        Обучение двух моделей: для сроков и стоимости
        
        Args:
            X_train, X_test: Признаки (train/test)
            y_duration_train, y_duration_test: Целевая переменная - сроки
            y_cost_train, y_cost_test: Целевая переменная - стоимость
        """
        print("="*60)
        print("НАЧАЛО ОБУЧЕНИЯ МОДЕЛЕЙ")
        print("="*60)
        
        # === МОДЕЛЬ ДЛЯ ПРОГНОЗА СРОКОВ ===
        print("\n📊 Обучение модели для прогноза СРОКОВ...")
        
        self.model_duration = CatBoostRegressor(
            iterations=1500,
            learning_rate=0.03,
            depth=6,
            l2_leaf_reg=3.5,
            early_stopping_rounds=50,
            verbose=100
        )
        
        self.model_duration.fit(
            X_train, 
            y_duration_train,
            eval_set=(X_test, y_duration_test),
            use_best_model=True
        )
        
        # Оценка модели сроков
        duration_pred = self.model_duration.predict(X_test)
        duration_mae = mean_absolute_error(y_duration_test, duration_pred)
        duration_r2 = r2_score(y_duration_test, duration_pred)
        
        print(f"✓ Модель сроков обучена")
        print(f"  MAE: {duration_mae:.2f} дней")
        print(f"  R²: {duration_r2:.4f}")
        
        # === МОДЕЛЬ ДЛЯ ПРОГНОЗА СТОИМОСТИ ===
        print("\n💰 Обучение модели для прогноза СТОИМОСТИ...")
        
        self.model_cost = CatBoostRegressor(
            iterations=1500,
            learning_rate=0.03,
            depth=6,
            l2_leaf_reg=3.5,
            early_stopping_rounds=50,
            verbose=100
        )
        
        self.model_cost.fit(
            X_train, 
            y_cost_train,
            eval_set=(X_test, y_cost_test),
            use_best_model=True
        )
        
        # Оценка модели стоимости
        cost_pred = self.model_cost.predict(X_test)
        cost_mae = mean_absolute_error(y_cost_test, cost_pred)
        cost_r2 = r2_score(y_cost_test, cost_pred)
        
        print(f"✓ Модель стоимости обучена")
        print(f"  MAE: {cost_mae:.2f} руб.")
        print(f"  R²: {cost_r2:.4f}")
        
        # Сохранение моделей
        self.save_models()
        
        print("\n" + "="*60)
        print("ОБУЧЕНИЕ ЗАВЕРШЕНО")
        print("="*60)
        
        return {
            'duration': {
                'model': self.model_duration,
                'mae': duration_mae,
                'r2': duration_r2
            },
            'cost': {
                'model': self.model_cost,
                'mae': cost_mae,
                'r2': cost_r2
            }
        }
    
    def save_models(self):
        """Сохранение обученных моделей на диск"""
        if self.model_duration:
            path = self.models_dir / "model_duration.cbm"
            self.model_duration.save_model(str(path))
            print(f"✓ Модель сроков сохранена: {path}")
        
        if self.model_cost:
            path = self.models_dir / "model_cost.cbm"
            self.model_cost.save_model(str(path))
            print(f"✓ Модель стоимости сохранена: {path}")
    
    def load_models(self):
        """Загрузка моделей с диска"""
        duration_path = self.models_dir / "model_duration.cbm"
        cost_path = self.models_dir / "model_cost.cbm"
        
        if not duration_path.exists() or not cost_path.exists():
            raise FileNotFoundError("Модели не найдены. Сначала обучите их.")
        
        self.model_duration = CatBoostRegressor()
        self.model_duration.load_model(str(duration_path))
        
        self.model_cost = CatBoostRegressor()
        self.model_cost.load_model(str(cost_path))
        
        print("✓ Модели загружены")