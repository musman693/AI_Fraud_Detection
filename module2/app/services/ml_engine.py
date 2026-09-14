import numpy as np
from sklearn.ensemble import IsolationForest

_model = IsolationForest(contamination=0.1, random_state=42)
_dummy_train_data = np.array([
    [50.0, 100, 1], [100.0, 200, 0], [25.0, 30, 2], 
    [120.0, 150, 1], [30.0, 50, 0], [1000.0, 1, 10]
])
_model.fit(_dummy_train_data)

def predict_anomaly_score(amount: float, account_age: int, velocity: int) -> float:
    X = np.array([[amount, account_age, velocity]])
    raw_score = _model.decision_function(X)[0]
    normalized_score = max(0.0, min(100.0, (0.5 - raw_score) * 100))
    return round(normalized_score, 2)