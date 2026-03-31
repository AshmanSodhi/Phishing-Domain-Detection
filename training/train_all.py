# training/train_all.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import joblib
from training.train_rf  import train_random_forest
from training.train_xgb import train_xgboost
from training.train_svm import train_svm

def train_all():
    print("=" * 55)
    print("PHASE 4 — MODEL TRAINING")
    print("=" * 55)

    rf_model,  rf_auc  = train_random_forest()
    xgb_model, xgb_auc = train_xgboost()
    svm_model, svm_auc = train_svm()

    results = {
        "Random Forest": (rf_model,  rf_auc),
        "XGBoost":       (xgb_model, xgb_auc),
        "SVM":           (svm_model, svm_auc),
    }

    print("\n" + "=" * 55)
    print("FINAL COMPARISON")
    print("=" * 55)
    print(f"{'Model':<20} {'ROC-AUC':>10}")
    print("-" * 35)
    for name, (_, auc) in sorted(results.items(),
                                  key=lambda x: x[1][1],
                                  reverse=True):
        marker = " ← best" if auc == max(a for _,a in results.values()) else ""
        print(f"{name:<20} {auc:>10.4f}{marker}")

    best_name, (best_model, best_auc) = max(
        results.items(), key=lambda x: x[1][1]
    )

    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/best_model.pkl")

    # save metadata
    with open("models/best_model_info.txt", "w") as f:
        f.write(f"Best model : {best_name}\n")
        f.write(f"ROC-AUC    : {best_auc:.4f}\n")
        f.write(f"RF AUC     : {rf_auc:.4f}\n")
        f.write(f"XGB AUC    : {xgb_auc:.4f}\n")
        f.write(f"SVM AUC    : {svm_auc:.4f}\n")

    print(f"\nBest model : {best_name} (AUC = {best_auc:.4f})")
    print("Saved → models/best_model.pkl")
    print("Saved → models/best_model_info.txt")

if __name__ == "__main__":
    train_all()