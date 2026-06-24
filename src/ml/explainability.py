"""
Модуль объяснимости моделей с помощью SHAP.
"""
import shap
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from src.config import Config


class SHAPExplainer:
    """SHAP-анализ для объяснения прогнозов"""
    
    def __init__(self, model):
        self.model = model
        self.explainer = shap.TreeExplainer(model)
    
    def explain_prediction(self, X_sample):
        """
        Вычисление SHAP-значений для образца данных
        
        Args:
            X_sample: DataFrame с признаками для объяснения
        
        Returns:
            shap_values: SHAP-значения
        """
        shap_values = self.explainer.shap_values(X_sample)
        return shap_values
    
    def plot_summary(self, X_sample, save_path=None):
        """
        Построение summary plot (важность признаков)
        
        Args:
            X_sample: DataFrame с признаками
            save_path: Путь для сохранения графика (опционально)
        """
        shap_values = self.explain_prediction(X_sample)
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_sample, show=False)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Summary plot сохранен: {save_path}")
        
        plt.close()
    
    def plot_force(self, X_sample, instance_index=0, save_path=None):
        """
        Построение force plot для конкретного прогноза
        
        Args:
            X_sample: DataFrame с признаками
            instance_index: Индекс экземпляра для объяснения
            save_path: Путь для сохранения (опционально)
        """
        shap_values = self.explain_prediction(X_sample)
        
        plt.figure(figsize=(12, 6))
        shap.force_plot(
            self.explainer.expected_value,
            shap_values[instance_index],
            X_sample.iloc[instance_index],
            matplotlib=True,
            show=False
        )
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Force plot сохранен: {save_path}")
        
        plt.close()
    
    def get_feature_importance(self, X_sample):
        """
        Получение важности признаков (средние абсолютные SHAP-значения)
        
        Returns:
            DataFrame с важностью признаков
        """
        shap_values = self.explain_prediction(X_sample)
        
        # Для регрессии shap_values - это массив
        importance = pd.DataFrame({
            'feature': X_sample.columns,
            'importance': [abs(shap_values[:, i]).mean() for i in range(len(X_sample.columns))]
        }).sort_values('importance', ascending=False)
        
        return importance