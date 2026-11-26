from fastapi import HTTPException
from core.audit import record
from core.db import transaction
from core.queueing import result,submit
from domain.evidence_tables import counts,issues
from domain.labels import CaseState,IssueState
from domain.learning import FEATURES
from domain.manifest import cases,placements
from domain.readback import all_rows,one


def check(item,form,placement):
    if item['state']!=CaseState.AT_TABLE:
        raise HTTPException(409,'独占箱码尚未交台、撞码锁定或已经结单')
    if not 0<=form['return_count']<=form['table_count']<=placement['outbound_count']:
        raise HTTPException(409,'出借、台面与回收数量必须逐段不增')


def probe(form,user):
    with transaction() as conn:
        placement=one(conn,placements,form.placement_code)
        item=one(conn,cases,placement['case_code'])
        raw=form.model_dump()
        check(item,raw,placement)
        out=placement['outbound_count']
        capacity=item['capacity']
        inputs={'outbound_delta':(capacity-out)/capacity,
                'table_delta':(out-form.table_count)/capacity,
                'return_delta':(form.table_count-form.return_count)/capacity,
                **{name:raw[name] for name in FEATURES[3:]}}
    return submit(user,{'counts':raw,'features':inputs})


def certify(form,user):
    job=result(user,form.token)
    raw=job['input']['counts']
    label=job['result']
    with transaction() as conn:
        placement=one(conn,placements,raw['placement_code'])
        item=one(conn,cases,placement['case_code'],lock=True)
        check(item,raw,placement)
        missing=item['capacity']-raw['return_count']
        conn.execute(counts.insert().values(code=form.code,**raw,missing=missing,
            model_segment=label['model_segment'],votes=label['votes'],compute_token=form.token,signed_by=user['sub']))
        if missing:
            code='LOSS-'+form.code[:21]
            conn.execute(issues.insert().values(code=code,case_code=item['code'],placement_code=placement['code'],
                         frame_code=form.code,category='count_loss',state=IssueState.OPEN))
            state=CaseState.LOCKED
        else:
            state=CaseState.CLOSED
        conn.execute(cases.update().where(cases.c.code==item['code']).values(state=state))
        record(conn,user,f'capture:{form.code}:{missing}')
        return one(conn,counts,form.code)
