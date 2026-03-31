# training/train_svm.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import joblib
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import (classification_report,
                              roc_auc_score,
                              confusion_matrix)
from training.split import load_and_split

def train_svm():
    X_train, X_test, y_train, y_test = load_and_split()

    # SVM is O(n²) — subsample train set to keep it fast
    MAX_TRAIN = 10000
    if len(X_train) > MAX_TRAIN:
        print(f"[SVM] Subsampling train to {MAX_TRAIN:,} rows for speed...")
        df_tmp = pd.DataFrame(X_train)
        df_tmp["label"] = y_train.values
        df_tmp = df_tmp.groupby("label", group_keys=False).apply(
            lambda x: x.sample(
                min(len(x), MAX_TRAIN // 2),
                random_state=42
            )
        )
        X_train = df_tmp.drop(columns=["label"])
        y_train = df_tmp["label"]

    print("\n[SVM] Starting GridSearchCV...")
    param_grid = {
        "C":      [0.1, 1, 10],
        "kernel": ["rbf", "linear"],
        "gamma":  ["scale", "auto"],
    }

    cv   = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    grid = GridSearchCV(
        SVC(probability=True, random_state=42),
        param_grid,
        cv=cv,
        scoring="f1",
        n_jobs=-1,
        verbose=1
    )
    grid.fit(X_train, y_train)

    best   = grid.best_estimator_
    y_pred = best.predict(X_test)
    y_prob = best.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)

    print("\n=== SVM Results ===")
    print(f"Best params : {grid.best_params_}")
    print(f"ROC-AUC     : {auc:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred,
                                 target_names=["legit", "phishing"]))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    os.makedirs("models", exist_ok=True)
    joblib.dump(best, "models/svm_model.pkl")
    print("Saved → models/svm_model.pkl")

    return best, auc

if __name__ == "__main__":
    train_svm()