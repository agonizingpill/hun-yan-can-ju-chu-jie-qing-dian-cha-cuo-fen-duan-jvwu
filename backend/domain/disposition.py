from fastapi import HTTPException
from core.audit import record
from core.db import transaction
from domain.evidence_tables import counts,issues
from domain.labels import CaseState,IssueState,Segment,TableState
from domain.manifest import banquet_tables,cases,placements
from domain.readback import all_rows,one


def attribute(code,form,user):
    with transaction() as conn:
        original=one(conn,issues,code)
        one(conn,cases,original['case_code'],lock=True)
        issue=one(conn,issues,code,lock=True)
        if issue['state']!=IssueState.OPEN:
            raise HTTPException(409,'差错已经归责或结案')
        if issue['category']!='count_loss':
            raise HTTPException(409,'跨宴台撞码须核实箱签并解除锁定后才能清点')
        if form.segment==Segment.BALANCED:
            raise HTTPException(409,'已确认缺件须指定一个实际交接段')
        conn.execute(issues.update().where(issues.c.code==code).values(state=IssueState.ASSIGNED,
                     responsible_segment=form.segment,responsible_name=form.person))
        record(conn,user,f'assign:{code}:{form.segment}')
        return one(conn,issues,code)


def resolve(code,form,user):
    with transaction() as conn:
        original=one(conn,issues,code)
        item=one(conn,cases,original['case_code'],lock=True)
        issue=one(conn,issues,code,lock=True)
        placement=one(conn,placements,issue['placement_code'])
        if issue['state']==IssueState.RESOLVED:
            raise HTTPException(409,'差错已经结案')
        if form.correctly_labeled_table!=placement['table_code'] or form.witnessed_tag!=item['lid_tag']:
            raise HTTPException(409,'复核宴台或箱签与最初交接不符')
        if issue['category']=='label_conflict':
            if issue['state']!=IssueState.OPEN or form.counted!=placement['outbound_count']:
                raise HTTPException(409,'撞码解锁须清点原出借数量')
            state=CaseState.AT_TABLE
        else:
            if issue['state']!=IssueState.ASSIGNED:
                raise HTTPException(409,'先明确责任交接段和责任人')
            frame=one(conn,counts,issue['frame_code'])
            if form.counted!=frame['return_count']:
                raise HTTPException(409,'签结数量必须等于实际回收读数')
            state=CaseState.CLOSED
        conn.execute(issues.update().where(issues.c.code==code).values(state=IssueState.RESOLVED,
                     released_count=form.counted,resolved_by=user['sub']))
        conn.execute(cases.update().where(cases.c.code==item['code']).values(state=state))
        record(conn,user,f'resolve:{code}:{state}')
        return one(conn,issues,code)


def clear_table(code,user):
    with transaction() as conn:
        table=one(conn,banquet_tables,code,lock=True)
        if table['state']==TableState.CLEARED:
            raise HTTPException(409,'宴台已经撤席')
        allocated=all_rows(conn,placements,placements.c.table_code==code)
        if not allocated:
            raise HTTPException(409,'没有宴台出借凭证')
        for line in sorted(allocated,key=lambda item:item['case_code']):
            if one(conn,cases,line['case_code'],lock=True)['state']!=CaseState.CLOSED:
                raise HTTPException(409,'仍有在台或锁定餐具箱，先完成清点与差错交接')
        conn.execute(banquet_tables.update().where(banquet_tables.c.code==code).values(state=TableState.CLEARED))
        record(conn,user,f'clear:{code}')
        return one(conn,banquet_tables,code)
