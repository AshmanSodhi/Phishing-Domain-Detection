# debug_features.py
import joblib
features = joblib.load("models/selected_features.pkl")
print("Selected features:")
for f in features:
    print(" ", f)