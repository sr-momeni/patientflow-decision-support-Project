"""Machine Learning predictor for high-urgency patient arrivals."""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
import sklearn
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

FEATURE_NAMES = ('hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'ed_occupancy',
                 'icu_occupancy', 'arrivals_15m', 'arrivals_30m', 'arrivals_1h',
                 'arrivals_4h', 'active_ctas1', 'active_ctas2', 'active_ctas3')
FEATURE_SCHEMA = 'causal-state-v2-13'

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
            dow_sin, dow_cos, ed_occupancy, icu_occupancy,
            *[(rates or {}).get(k, 0) for k in ('15m', '30m', '1h', '4h')],
            *[(acuity_counts or {}).get(k, 0) for k in (1, 2, 3)]
        ]
        return np.array(features).reshape(1, -1)
    
    def train(self, features_matrix: np.ndarray, labels: np.ndarray,
              validation=None) -> Dict:
        """Fit supplied training-only rows; no leaky random row split.

        Caller must supply independent stream/day blocks for validation. No
        held-out accuracy is implied when validation is omitted.
        """
        if features_matrix.ndim != 2 or features_matrix.shape[1] != len(FEATURE_NAMES):
            raise ValueError('Expected the shared 13-feature causal schema')
        self.model.fit(features_matrix, labels)
        self.is_trained = True
        result = {'train_size': len(labels), 'test_size': 0}
        if validation is not None:
            X, y = validation
            pred = self.model.predict(X)
            result.update(mse=mean_squared_error(y, pred), mae=mean_absolute_error(y, pred),
                          r2=r2_score(y, pred), test_size=len(y))
        return result

    def predict(self, timestamp: datetime, ed_occupancy: float, 
                icu_occupancy: float, rates: Dict[str, float],
                acuity_counts: Dict[int, int]) -> float:
        """
        Predict expected count of high-urgency arrivals in next window.
        
        Returns:
            float: Expected number of L1/L2 patients.
        """
        if not self.is_trained:
            return 0.0
            
        features = self._extract_features(timestamp, ed_occupancy, icu_occupancy, rates, acuity_counts)
        expected_count = self.model.predict(features)[0]
        
        # Count can't be negative
        return max(0.0, float(expected_count))
    
    def save(self, path: str):
        """Save trained model to disk."""
        joblib.dump({
            'feature_schema': FEATURE_SCHEMA,
            'feature_names': FEATURE_NAMES,
            'sklearn_version': sklearn.__version__,
            'model': self.model,
            'prediction_window': self.prediction_window_minutes,
            'is_trained': self.is_trained
        }, path)
    
    @classmethod
    def load(cls, path: str):
        """Load trained model from disk."""
        data = joblib.load(path)
        if data.get('feature_schema') != FEATURE_SCHEMA or tuple(data.get('feature_names', ())) != FEATURE_NAMES:
            raise ValueError('Legacy/incompatible feature schema: retrain with the v2 evaluation workflow; original file is preserved')
        if data.get('sklearn_version') != sklearn.__version__:
            raise ValueError('Model sklearn version differs; reproduce in the recorded environment or retrain')
        if data['model'].n_features_in_ != len(FEATURE_NAMES):
            raise ValueError('Model feature count does not match its metadata')
        predictor = cls(prediction_window_minutes=data['prediction_window'])
        predictor.model = data['model']
        predictor.is_trained = data['is_trained']
        return predictor
