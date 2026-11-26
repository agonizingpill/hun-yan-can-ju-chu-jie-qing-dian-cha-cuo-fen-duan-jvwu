from fastapi import APIRouter,Depends
from core.auth import actor,allow
from core.db import transaction
from core.roles import REVIEW,WRITE
from domain import counting,demo_governance,disposition,model_registry,placement,readback
from domain.forms import CountFrame,Custody,Inspection,Place,Revision,Signature

room=APIRouter(prefix='/room')
frame=APIRouter(prefix='/counts')
claims=APIRouter(prefix='/custody')
models=APIRouter(prefix='/models')
routers=(room,frame,claims,models)


@room.get('')
def floor(user=Depends(actor)):
    return readback.layout()


@room.post('/placement',status_code=201)
def place(form:Place,user=Depends(actor)):
    allow(user,WRITE)
    return placement.put_at_table(form,user)


@room.post('/{code}/clear')
def clear(code:str,user=Depends(actor)):
    allow(user,REVIEW)
    return disposition.clear_table(code,user)


@frame.get('')
def frames(user=Depends(actor)):
    return readback.frames()


@frame.get('/active-model')
def active_model(user=Depends(actor)):
    with transaction() as conn:
        model_registry.ensure_baseline(conn)
        return {'active_version':model_registry.active_version(conn)['code']}


@frame.post('/review',status_code=202)
def propose(form:CountFrame,user=Depends(actor)):
    allow(user,WRITE)
    return counting.probe(form,user)


@frame.post('/sign',status_code=201)
def sign(form:Signature,user=Depends(actor)):
    allow(user,WRITE)
    return counting.certify(form,user)


@claims.get('')
def cases(user=Depends(actor)):
    return readback.exceptions()


@claims.post('/{code}/assign')
def assign(code:str,form:Custody,user=Depends(actor)):
    allow(user,REVIEW)
    return disposition.attribute(code,form,user)


@claims.post('/{code}/resolve')
def resolve(code:str,form:Inspection,user=Depends(actor)):
    allow(user,REVIEW)
    return disposition.resolve(code,form,user)


@claims.post('/{code}/revise')
def revise(code:str,form:Revision,user=Depends(actor)):
    allow(user,REVIEW)
    return model_registry.revise_attribution(code,form,user)


@models.get('')
def model_overview(user=Depends(actor)):
    return model_registry.governance_overview()


@models.post('/train',status_code=201)
def train(user=Depends(actor)):
    allow(user,REVIEW)
    return model_registry.train_candidate(user)


@models.post('/{version}/promote')
def promote(version:str,user=Depends(actor)):
    allow(user,REVIEW)
    return model_registry.evaluate_and_promote(version,user)


@models.post('/demo-dataset',status_code=201)
def demo_dataset(user=Depends(actor)):
    allow(user,REVIEW)
    return demo_governance.seed_governance_demo(user)
