"""Machine Learning predictor for high-urgency patient arrivals."""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_recall_fscore_support

class HighUrgencyPredictor:
    """Predicts probability of high-urgency patient arriving in next time window."""
    
    def __init__(self, prediction_window_minutes=30):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # Handle class imbalance
        )
        self.prediction_window_minutes = prediction_window_minutes
        self.is_trained = False
        
    def _extract_features(self, timestamp: datetime, current_ed_occupancy: float, 
                         current_icu_occupancy: float, recent_arrival_rate: float) -> np.ndarray:
        """Extract features for a given state."""
        features = [
            timestamp.hour,  # Hour of day (0-23)
            timestamp.minute,  # Minute (0-59)
            timestamp.weekday(),  # Day of week (0=Monday, 6=Sunday)
            current_ed_occupancy,  # % of ED beds occupied
            current_icu_occupancy,  # % of ICU beds occupied
            recent_arrival_rate,  # Patients per hour in last 2 hours
        ]
        return np.array(features).reshape(1, -1)
    
    def train(self, arrivals_data: List[Dict]) -> Dict:
        """
        Train the model on historical arrival data.
        
        Args:
            arrivals_data: List of dicts with keys: 
                - 'arrival_ts': datetime
                - 'urgency': int
                - 'ed_occupancy': float
                - 'icu_occupancy': float
                - 'recent_rate': float
        
        Returns:
            Dict with training metrics
        """
        X = []
        y = []
        
        for i, record in enumerate(arrivals_data):
            # Features
            ts = record['arrival_ts']
            features = [
                ts.hour,
                ts.minute,
                ts.weekday(),
                record.get('ed_occupancy', 0.5),
                record.get('icu_occupancy', 0.5),
                record.get('recent_rate', 10.0),
            ]
            X.append(features)
            
            # Label: Was there a high-urgency arrival in next window?
            # We need to look ahead in the data
            future_window_end = ts + timedelta(minutes=self.prediction_window_minutes)
            has_urgent = False
            
            for j in range(i, min(i + 50, len(arrivals_data))):  # Look ahead
                next_arrival = arrivals_data[j]
                next_ts = next_arrival['arrival_ts']
                
                if next_ts > future_window_end:
                    break
                    
                if next_arrival['urgency'] == 1:  # Urgency level 1
                    has_urgent = True
                    break
                    
            y.append(1 if has_urgent else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary'
        )
        
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'positive_class_ratio': y.mean()
        }
    
    def predict(self, timestamp: datetime, ed_occupancy: float, 
                icu_occupancy: float, recent_rate: float) -> float:
        """
        Predict probability of high-urgency arrival in next window.
        
        Returns:
            Probability between 0 and 1
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
            
        features = self._extract_features(timestamp, ed_occupancy, icu_occupancy, recent_rate)
        proba = self.model.predict_proba(features)[0, 1]  # Probability of class 1
        return proba
    
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
