from fastapi import HTTPException
from core.audit import record
from core.db import transaction
from domain.evidence_tables import issues
from domain.labels import CaseState, IssueState, TableState
from domain.manifest import banquet_tables,cases,placements
from domain.readback import one,placement_for


def put_at_table(form,user):
    with transaction() as conn:
        table=one(conn,banquet_tables,form.table_code,lock=True)
        item=one(conn,cases,form.case_code,lock=True)
        if item['lid_tag']!=form.lid_tag:
            raise HTTPException(409,'箱盖封签和箱码不匹配')
        if table['state']==TableState.CLEARED:
            raise HTTPException(409,'已撤宴台不能再次收箱')
        if item['state']==CaseState.LOCKED:
            raise HTTPException(409,'该箱码已锁，先复核差错再移交')
        if item['state']==CaseState.CLOSED:
            raise HTTPException(409,'该收箱记录已完成，本场次不再复用')
        old=placement_for(conn,item['code'])
        if old:
            if old['table_code']==form.table_code:
                raise HTTPException(409,'此箱已在同一宴台签收')
            code='LOCK-'+form.code[:21]
            conn.execute(issues.insert().values(code=code,case_code=item['code'],placement_code=old['code'],
                         conflicting_table=table['code'],category='label_conflict',state=IssueState.OPEN))
            conn.execute(cases.update().where(cases.c.code==item['code']).values(state=CaseState.LOCKED))
            record(conn,user,f'label_conflict:{code}')
            return {'state':CaseState.LOCKED,'issue_code':code,'expected_table':old['table_code'],'scanned_table':table['code']}
        if not min(item['capacity'],table['seats'])<=form.outbound_count<=item['capacity']:
            raise HTTPException(409,'出借件数小于宴台需求或超出整箱容量')
        conn.execute(placements.insert().values(code=form.code,table_code=table['code'],case_code=item['code'],
            outbound_count=form.outbound_count,counted_by=user['sub']))
        conn.execute(cases.update().where(cases.c.code==item['code']).values(state=CaseState.AT_TABLE))
        record(conn,user,f'placement:{form.code}')
        return {'state':CaseState.AT_TABLE,'placement':one(conn,placements,form.code)}
