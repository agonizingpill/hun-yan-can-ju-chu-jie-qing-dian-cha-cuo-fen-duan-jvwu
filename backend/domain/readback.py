from fastapi import HTTPException
from sqlalchemy import select

from core.db import transaction
from domain.evidence_tables import counts, issues
from domain.labels import IssueState
from domain.manifest import banquet_tables,cases,placements


def one(conn,table,code,lock=False):
    statement=select(table).where(table.c.code==code)
    row=conn.execute(statement.with_for_update() if lock else statement).mappings().first()
    if row is None:
        raise HTTPException(404,f'编号 {code} 不存在')
    return dict(row)


def all_rows(conn,table,*filters):
    query=select(table).where(*filters).order_by(table.c.code.desc()).limit(100)
    return [dict(row) for row in conn.execute(query).mappings()]


def placement_for(conn,case_code):
    rows=all_rows(conn,placements,placements.c.case_code==case_code)
    return rows[0] if rows else None


def has_lock(conn,case_code):
    return bool(all_rows(conn,issues,issues.c.case_code==case_code,issues.c.state!=IssueState.RESOLVED))


def layout():
    with transaction() as conn:
        return {'tables':all_rows(conn,banquet_tables),'cases':all_rows(conn,cases),'placements':all_rows(conn,placements)}


def frames():
    with transaction() as conn:
        return all_rows(conn,counts)


def exceptions():
    with transaction() as conn:
        return all_rows(conn,issues)
