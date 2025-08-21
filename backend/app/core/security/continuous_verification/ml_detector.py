from sklearn.ensemble import IsolationForest
import numpy as np
import joblib
from typing import List, Dict, Any

class MLAnomalyDetector:
    """機械学習による異常検出"""
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
        
    def extract_features(self, request_data: Dict[str, Any]) -> np.ndarray:
        """リクエストから特徴量を抽出"""
        features = []
        
        # 時間関連の特徴量
        hour = request_data.get('hour', 0)
        day_of_week = request_data.get('day_of_week', 0)
        
        # リクエストパターンの特徴量
        endpoint = request_data.get('endpoint', '')
        method = request_data.get('method', '')
        
        # IP関連の特徴量
        ip_risk = request_data.get('ip_risk', 0)
        
        features = [hour, day_of_week, ip_risk]
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict[str, Any]]):
        """モデルの訓練"""
        features = []
        for data in training_data:
            feature_vector = self.extract_features(data)
            features.append(feature_vector.flatten())
        
        X = np.array(features)
        self.model.fit(X)
        self.is_trained = True
        
    def detect_anomaly(self, request_data: Dict[str, Any]) -> bool:
        """異常検出"""
        if not self.is_trained:
            return False
        
        features = self.extract_features(request_data)
        prediction = self.model.predict(features)
        
        # -1: 異常, 1: 正常
        return prediction[0] == -1
