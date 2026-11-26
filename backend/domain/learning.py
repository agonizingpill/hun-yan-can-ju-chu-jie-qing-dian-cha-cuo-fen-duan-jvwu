from functools import lru_cache
from random import Random

from sklearn.ensemble import BaggingClassifier
from sklearn.metrics import accuracy_score,confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from domain.labels import Segment

FEATURES=('outbound_delta','table_delta','return_delta','covered_ratio','blur_share','edge_overlap','handoff_gap')
CENTERS={
    Segment.BALANCED:(.02,.02,.02,.15,.13,.18,.12),
    Segment.OUTBOUND:(.39,.08,.07,.22,.18,.28,.22),
    Segment.TABLE:(.09,.35,.08,.72,.17,.74,.32),
    Segment.COLLECTION:(.08,.10,.37,.24,.62,.27,.76),
}
MODEL='bag-linear-svc-20261124'


def simulated(seed,per_kind):
    rng=Random(seed)
    examples,labels=[],[]
    for label,center in CENTERS.items():
        for _ in range(per_kind):
            examples.append([min(1,max(0,rng.gauss(value,.027))) for value in center])
            labels.append(str(label))
    return examples,labels


@lru_cache(maxsize=1)
def fitted():
    train,labels=simulated(404,50)
    holdout,truth=simulated(81,14)
    estimator=make_pipeline(StandardScaler(),LinearSVC(dual=False,random_state=91))
    model=BaggingClassifier(estimator=estimator,n_estimators=48,random_state=92,max_samples=.8,n_jobs=1)
    model.fit(train,labels)
    pred=model.predict(holdout)
    metrics={'train':len(train),'holdout':len(truth),'accuracy':float(accuracy_score(truth,pred)),
             'classes':list(model.classes_),'matrix':confusion_matrix(truth,pred,labels=model.classes_).tolist()}
    return model,metrics


def calculate(payload):
    model,metrics=fitted()
    values=[[payload['features'][key] for key in FEATURES]]
    scores=model.predict_proba(values)[0].tolist()
    candidates=dict(zip(model.classes_,scores,strict=True))
    return {'model':MODEL,'model_segment':str(max(candidates,key=candidates.get)),
            'votes':candidates,'holdout':metrics}
