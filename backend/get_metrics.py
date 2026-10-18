import cultivation.train_recommendation as m
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import numpy as np


d = m.build_expanded_dataset()
X = d[m.FEATURE_COLUMNS]
y = d[m.TARGET_COLUMN]

print("=== DATASET DISTRIBUTION ===")
print("Total records:", len(d))
print("Number of classes (unique plants/labels):", y.nunique())
print("Samples per class:", y.value_counts().min(), "to", y.value_counts().max())

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y,
)

print("\nTrain records:", len(X_train))
print("Test records:", len(X_test))

print("\n=== MODEL PERFORMANCE (test set) ===")
for name in ["random_forest", "decision_tree", "gradient_boosting"]:
    pipe = Pipeline([
        ("preprocessor", m._build_preprocessor()),
        ("classifier", m._build_model(name)),
    ])
    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)

    print(f"\n{name}")
    print(f"  Accuracy:          {accuracy_score(y_test, preds):.4f}")
    print(f"  Precision (macro): {precision_score(y_test, preds, average='macro', zero_division=0):.4f}")
    print(f"  Recall (macro):    {recall_score(y_test, preds, average='macro', zero_division=0):.4f}")
    print(f"  F1-score (macro):  {f1_score(y_test, preds, average='macro', zero_division=0):.4f}")

print("\n=== RANDOM FOREST FEATURE IMPORTANCE ===")
rf_pipe = Pipeline([
    ("preprocessor", m._build_preprocessor()),
    ("classifier", m._build_model("random_forest")),
])
rf_pipe.fit(X_train, y_train)
feature_names = rf_pipe.named_steps["preprocessor"].get_feature_names_out()
importances = rf_pipe.named_steps["classifier"].feature_importances_
order = np.argsort(importances)[::-1]

for i in order:
    print(f"  {feature_names[i]}: {importances[i]:.4f}")