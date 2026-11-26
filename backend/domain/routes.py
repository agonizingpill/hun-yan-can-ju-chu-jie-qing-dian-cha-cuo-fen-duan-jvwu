from fastapi import APIRouter,Depends
from core.auth import actor,allow
from core.roles import REVIEW,WRITE
from domain import counting,disposition,placement,readback
from domain.forms import CountFrame,Custody,Inspection,Place,Signature

room=APIRouter(prefix='/room')
frame=APIRouter(prefix='/counts')
claims=APIRouter(prefix='/custody')
routers=(room,frame,claims)


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
