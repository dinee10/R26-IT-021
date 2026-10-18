# topk_metrics.py
# Run from: d:\Research project web\R26-IT-021\backend
# Command:  python topk_metrics.py

import cultivation.train_recommendation as m
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import numpy as np

d = m.build_expanded_dataset()
X = d[m.FEATURE_COLUMNS]
y = d[m.TARGET_COLUMN]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

pipe = Pipeline([
    ("preprocessor", m._build_preprocessor()),
    ("classifier", m._build_model("random_forest")),
])
pipe.fit(X_train, y_train)

# Standard top-1 accuracy (what you already have)
top1_preds = pipe.predict(X_test)
print("Top-1 accuracy:", round(accuracy_score(y_test, top1_preds), 4))

# Get class probabilities to compute top-k accuracy
probs = pipe.predict_proba(X_test)
classes = pipe.named_steps["classifier"].classes_


def topk_accuracy(y_true, probs, classes, k):
    y_true = np.array(y_true)
    top_k_idx = np.argsort(probs, axis=1)[:, -k:]  # indices of top-k highest-probability classes
    top_k_labels = classes[top_k_idx]               # convert indices to actual class labels
    hits = [y_true[i] in top_k_labels[i] for i in range(len(y_true))]
    return np.mean(hits)


for k in [1, 3, 5, 10]:
    acc = topk_accuracy(y_test, probs, classes, k)
    print(f"Top-{k} accuracy: {acc:.4f}  ({int(acc * len(y_test))}/{len(y_test)} correct)")

# Show a few example test rows: true label vs the model's top-5 guesses
print("\n=== SAMPLE PREDICTIONS (first 8 test rows) ===")
top5_idx = np.argsort(probs, axis=1)[:, -5:][:, ::-1]  # best guess first
for i in range(min(8, len(y_test))):
    true_label = y_test.iloc[i]
    guesses = classes[top5_idx[i]]
    print(f"  true={true_label!r:25} top5_guesses={list(guesses)}")