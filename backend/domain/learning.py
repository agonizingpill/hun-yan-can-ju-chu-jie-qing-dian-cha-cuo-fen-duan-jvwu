import os
import pickle
from functools import lru_cache
from pathlib import Path
from random import Random

from sklearn.ensemble import BaggingClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from domain.labels import LOSS_SEGMENTS, Segment

FEATURES = ('outbound_delta', 'table_delta', 'return_delta', 'covered_ratio',
            'blur_share', 'edge_overlap', 'handoff_gap')
CENTERS = {
    Segment.BALANCED: (.02, .02, .02, .15, .13, .18, .12),
    Segment.OUTBOUND: (.39, .08, .07, .22, .18, .28, .22),
    Segment.TABLE: (.09, .35, .08, .72, .17, .74, .32),
    Segment.COLLECTION: (.08, .10, .37, .24, .62, .27, .76),
}
# 系统自带的模拟兜底版：不依赖任何人工归责，永不作废，active 回退时由它接管。
BASELINE_VERSION = 'baseline-bag-linear-svc'
ARTIFACT_DIR = Path(os.environ.get('MODEL_ARTIFACT_DIR', '/results/models'))


def simulated(seed, per_kind):
    rng = Random(seed)
    examples, labels = [], []
    for label, center in CENTERS.items():
        for _ in range(per_kind):
            examples.append([min(1, max(0, rng.gauss(value, .027))) for value in center])
            labels.append(str(label))
    return examples, labels


@lru_cache(maxsize=1)
def baseline_bundle():
    train, labels = simulated(404, 50)
    holdout, truth = simulated(81, 14)
    estimator = make_pipeline(StandardScaler(), LinearSVC(dual=False, random_state=91))
    model = BaggingClassifier(estimator=estimator, n_estimators=48, random_state=92,
                              max_samples=.8, n_jobs=1)
    model.fit(train, labels)
    pred = model.predict(holdout)
    metrics = {'train': len(train), 'holdout': len(truth),
               'accuracy': float(accuracy_score(truth, pred)),
               'classes': list(model.classes_),
               'matrix': confusion_matrix(truth, pred, labels=model.classes_).tolist()}
    return model, metrics


def feature_vector(payload):
    return [payload['features'][key] for key in FEATURES]


def train_artifact(rows):
    """rows: list of dict，每条带 features(7 维 dict) 与 label(人工归责段)。"""
    train = [feature_vector({'features': row['features']}) for row in rows]
    labels = [row['label'] for row in rows]
    estimator = make_pipeline(StandardScaler(), LinearSVC(dual=False, random_state=91))
    model = BaggingClassifier(estimator=estimator, n_estimators=48, random_state=92,
                              max_samples=.8, n_jobs=1)
    model.fit(train, labels)
    counts = {segment: labels.count(str(segment)) for segment in LOSS_SEGMENTS}
    return model, {'train': len(rows), 'per_segment': counts, 'classes': list(model.classes_)}


def save_artifact(version, model, metrics):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / f'{version}.pkl'
    with path.open('wb') as handle:
        pickle.dump({'model': model, 'metrics': metrics, 'features': FEATURES}, handle)
    return str(path)


@lru_cache(maxsize=8)
def load_artifact(version):
    with (ARTIFACT_DIR / f'{version}.pkl').open('rb') as handle:
        return pickle.load(handle)


def predict_with(version, payload):
    if version == BASELINE_VERSION:
        model, metrics = baseline_bundle()
    else:
        bundle = load_artifact(version)
        model, metrics = bundle['model'], bundle['metrics']
    values = [feature_vector(payload)]
    scores = model.predict_proba(values)[0].tolist()
    candidates = dict(zip(model.classes_, scores, strict=True))
    return {'model': version, 'model_segment': str(max(candidates, key=candidates.get)),
            'votes': candidates, 'holdout': metrics}


def calculate(payload):
    # 由调用方（registry）在 payload 上指定钉住的版本；缺省回退 baseline。
    return predict_with(payload.get('model_version', BASELINE_VERSION), payload)


def miss_report(version, cases):
    """cases: list of dict，每条带 features 与 truth_segment。返回逐段漏判与逐箱预测。"""
    per_segment = {str(segment): 0 for segment in LOSS_SEGMENTS}
    rows = []
    for case in cases:
        prediction = predict_with(version, {'features': case['features']})
        predicted = prediction['model_segment']
        truth = case['truth_segment']
        missed = 0 if predicted == truth else 1
        if missed:
            per_segment[truth] += 1
        rows.append({'case_code': case['case_code'], 'predicted_segment': predicted,
                     'truth_segment': truth, 'missed': missed})
    return per_segment, rows
