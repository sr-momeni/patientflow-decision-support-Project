"""Machine Learning predictor for high-urgency patient arrivals."""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class HighUrgencyPredictor:
    """Predicts expected count of high-urgency (L1/L2) patients arriving in next time window."""
    
    def __init__(self, prediction_window_minutes=60):
        # We use HistGradientBoostingRegressor as it supports missing values, is fast,
        # and works well for tabular data.
        self.model = HistGradientBoostingRegressor(
            max_iter=100,
            max_depth=10,
            learning_rate=0.1,
            random_state=42
        )
        self.prediction_window_minutes = prediction_window_minutes
        self.is_trained = False
        
    def _extract_features(self, timestamp: datetime, ed_occupancy: float = 0.0, 
                         icu_occupancy: float = 0.0, rates: Dict[str, float] = None,
                         acuity_counts: Dict[int, int] = None) -> np.ndarray:
        """Extract features using cyclical time encoding."""
        
        # Cyclical encoding helps the model understand that 23:00 is close to 01:00
        hour_sin = np.sin(2 * np.pi * timestamp.hour / 24.0)
        hour_cos = np.cos(2 * np.pi * timestamp.hour / 24.0)
        dow_sin = np.sin(2 * np.pi * timestamp.weekday() / 7.0)
        dow_cos = np.cos(2 * np.pi * timestamp.weekday() / 7.0)
        
        features = [
            hour_sin, hour_cos,
            dow_sin, dow_cos
        ]
        return np.array(features).reshape(1, -1)
    
    def train(self, features_matrix: np.ndarray, labels: np.ndarray) -> Dict:
        """
        Train the regressor model.
        features_matrix: Pre-calculated features from historical data.
        labels: Actual count of L1/L2 arrivals in the target window.
        """
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            features_matrix, labels, test_size=0.2, random_state=42
        )
        
        # Train
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        return {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'train_size': len(X_train),
            'test_size': len(X_test),
        }
    
    def predict(self, timestamp: datetime, ed_occupancy: float, 
                icu_occupancy: float, rates: Dict[str, float],
                acuity_counts: Dict[int, int]) -> float:
        """
        Predict expected count of high-urgency arrivals in next window.
        
        Returns:
            float: Expected number of L1/L2 patients.
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
            
        features = self._extract_features(timestamp, ed_occupancy, icu_occupancy, rates, acuity_counts)
        expected_count = self.model.predict(features)[0]
        
        # Count can't be negative
        return max(0.0, float(expected_count))
    
    def save(self, path: str):
        """Save trained model to disk."""
        joblib.dump({
            'model': self.model,
            'prediction_window': self.prediction_window_minutes,
            'is_trained': self.is_trained
        }, path)
    
    @classmethod
    def load(cls, path: str):
        """Load trained model from disk."""
        data = joblib.load(path)
        predictor = cls(prediction_window_minutes=data['prediction_window'])
        predictor.model = data['model']
        predictor.is_trained = data['is_trained']
        return predictor
