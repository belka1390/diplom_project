"""
Модуль прогнозирования (инференс) для новых данных.
"""
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import Config
from .training import ModelTrainer
from .explainability import SHAPExplainer


class Predictor:
    """Прогнозирование сроков и стоимости для новых закупок"""
    
    def __init__(self):
        self.trainer = ModelTrainer()
        self.trainer.load_models()
    
    def predict(self, X_new):
        """
        Прогнозирование сроков и стоимости
        
        Args:
            X_new: DataFrame с признаками новой закупки
        
        Returns:
            dict с прогнозами
        """
        duration_pred = self.trainer.model_duration.predict(X_new)
        cost_pred = self.trainer.model_cost.predict(X_new)
        
        return {
            'duration_days': duration_pred,
            'cost_rub': cost_pred
        }
    
    def predict_with_explanation(self, X_new, instance_index=0):
        """
        Прогнозирование с объяснением через SHAP
        
        Args:
            X_new: DataFrame с признаками
            instance_index: Индекс экземпляра для объяснения
        
        Returns:
            dict с прогнозами и объяснениями
        """
        # Прогноз
        predictions = self.predict(X_new)
        
        # Объяснение для сроков
        explainer_duration = SHAPExplainer(self.trainer.model_duration)
        shap_duration = explainer_duration.explain_prediction(X_new)
        
        # Объяснение для стоимости
        explainer_cost = SHAPExplainer(self.trainer.model_cost)
        shap_cost = explainer_cost.explain_prediction(X_new)
        
        # Топ-5 важных признаков для сроков
        importance_duration = explainer_duration.get_feature_importance(X_new).head(5)
        
        # Топ-5 важных признаков для стоимости
        importance_cost = explainer_cost.get_feature_importance(X_new).head(5)
        
        return {
            'predictions': predictions,
            'explanations': {
                'duration': {
                    'shap_values': shap_duration[instance_index],
                    'top_features': importance_duration
                },
                'cost': {
                    'shap_values': shap_cost[instance_index],
                    'top_features': importance_cost
                }
            }
        }