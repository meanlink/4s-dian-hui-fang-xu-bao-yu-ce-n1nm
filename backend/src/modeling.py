from datetime import date
import json
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

FEATURES = ["service_gap_days", "policy_days_left", "annual_visits", "annual_spend", "satisfaction"]
FEATURE_LABELS = {
    "service_gap_days": "距最近保养天数",
    "policy_days_left": "距保单到期天数",
    "annual_visits": "近一年保养次数",
    "annual_spend": "近一年维修金额",
    "satisfaction": "最近满意度",
}


def _training_set():
    rng = np.random.default_rng(1054)
    X = rng.normal(0, 1, size=(600, 5))
    signal = -0.8 * X[:, 0] - 0.55 * X[:, 1] + 0.95 * X[:, 2] + 0.35 * X[:, 3] + 0.9 * X[:, 4]
    y = (signal + rng.normal(0, 0.8, size=600) > 0).astype(int)
    return X, y


def _model():
    X, y = _training_set()
    model = GradientBoostingClassifier(n_estimators=50, max_depth=2, learning_rate=0.08, random_state=1054)
    model.fit(X, y)
    return model, X.mean(axis=0), X.std(axis=0)


def build_features(owner, events, today=date(2026, 11, 21)):
    latest = max(events, key=lambda item: item["service_date"]) if events else None
    recent = [item for item in events if (today - item["service_date"]).days <= 365]
    gap = (today - latest["service_date"]).days if latest else 999
    policy_left = (owner["policy_expires"] - today).days
    visits = len(recent)
    spend = sum(float(item["amount"]) for item in recent) / 10000
    satisfaction = float(latest["satisfaction"]) if latest else 2.5
    return np.array([[gap / 90, policy_left / 180, visits / 6, spend, satisfaction / 5]], dtype=float), {
        "service_gap_days": gap,
        "policy_days_left": policy_left,
        "annual_visits": visits,
        "annual_spend": round(spend * 10000, 2),
        "satisfaction": satisfaction,
    }


def predict(owner, events):
    model, mean, std = _model()
    raw, values = build_features(owner, events)
    scaled = (raw - mean) / std
    score = float(model.predict_proba(scaled)[0, 1])
    baseline = model.predict_proba(np.zeros((1, 5)))[0, 1]
    contributions = {}
    for idx, key in enumerate(FEATURES):
        ablated = scaled.copy()
        ablated[0, idx] = 0
        contributions[key] = round(float(score - model.predict_proba(ablated)[0, 1]), 4)
    explanation = [{"key": key, "label": FEATURE_LABELS[key], "value": values[key], "contribution": contributions[key]} for key in FEATURES]
    explanation.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    return round(score, 4), explanation
