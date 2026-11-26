"""演示用已结案人工归责样本。

跨三个婚宴造数，每个婚宴都含后场装箱/宴台清点/撤席回收三段缺件箱，
保证按婚宴整组切分后，训练集与验收集都覆盖三个缺件段。
数据直接以结案状态落库，模拟复核员已人工归责并签结的真实历史。
"""
from sqlalchemy import select

from core.audit import record
from core.db import transaction
from domain import learning
from domain.evidence_tables import counts, issues
from domain.labels import CaseState, IssueState, Segment
from domain.manifest import banquet_tables, cases, placements

PARTIES = (
    ('MH-P01', '瑞和婚宴', '牡丹厅'),
    ('MH-P02', '瑞和婚宴', '牡丹厅'),
    ('MH-Q01', '景福婚宴', '海棠厅'),
    ('MH-Q02', '景福婚宴', '海棠厅'),
    ('MH-S01', '永泰婚宴', '金桂厅'),
    ('MH-S02', '永泰婚宴', '金桂厅'),
)

# 每个宴台三个箱，分别对应三个缺件责任段。
SEGMENT_PLAN = (
    (Segment.OUTBOUND, (10, 10, 7), (0.30, 0.20, 0.26, 0.24)),
    (Segment.TABLE, (12, 8, 8), (0.70, 0.18, 0.72, 0.30)),
    (Segment.COLLECTION, (10, 9, 5), (0.24, 0.60, 0.28, 0.74)),
)


def _token(value):
    from hashlib import md5
    return md5(value.encode()).hexdigest()


def seed_governance_demo(user):
    created = 0
    with transaction() as conn:
        marker = conn.scalar(select(counts.c.code).where(counts.c.code == 'CT-DM-P01-1'))
        if marker:
            return {'created': 0, 'note': '演示归责样本已存在，跳过'}

        for table_code, party, hall in PARTIES:
            conn.execute(banquet_tables.insert().values(
                code=table_code, hall=hall, party=party, seats=10,
                course='围席', runner='示范师傅', state='cleared'))
            for index, (segment, nums, ratios) in enumerate(SEGMENT_PLAN):
                seq = index + 1
                case_code = f'CASE-DM-{table_code[3:]}-{seq}'
                placement_code = f'PL-DM-{table_code[3:]}-{seq}'
                frame_code = f'CT-DM-{table_code[3:]}-{seq}'
                issue_code = f'LOSS-DM-{table_code[3:]}-{seq}'
                outbound, table_count, return_count = nums
                covered, blur, overlap, gap = ratios
                capacity = 12

                conn.execute(cases.insert().values(
                    code=case_code, dish='示范盖盘', capacity=capacity,
                    lid_tag=f'LID-DM-{table_code[3:]}-{seq}', state=CaseState.CLOSED))
                conn.execute(placements.insert().values(
                    code=placement_code, table_code=table_code, case_code=case_code,
                    outbound_count=outbound, counted_by=user['sub']))
                conn.execute(counts.insert().values(
                    code=frame_code, placement_code=placement_code,
                    table_count=table_count, return_count=return_count,
                    covered_ratio=covered, blur_share=blur, edge_overlap=overlap,
                    handoff_gap=gap, model_segment=str(segment),
                    model_version=learning.BASELINE_VERSION, votes={},
                    missing=capacity - return_count,
                    compute_token=_token(frame_code), signed_by=user['sub']))
                conn.execute(issues.insert().values(
                    code=issue_code, case_code=case_code, placement_code=placement_code,
                    frame_code=frame_code, category='count_loss', state=IssueState.RESOLVED,
                    responsible_segment=str(segment), responsible_name='示范复核员',
                    released_count=return_count, resolved_by=user['sub']))
                created += 1
        record(conn, user, f'demo-governance-seed:{created}')
    return {'created': created, 'parties': sorted({p[1] for p in PARTIES})}
