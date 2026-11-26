from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select

from core.audit import record
from core.db import transaction
from domain import learning
from domain.evidence_tables import counts, issues, now
from domain.labels import LOSS_SEGMENTS, IssueState, ModelStatus, Segment
from domain.manifest import banquet_tables, cases, placements
from domain.model_tables import (evaluation_campaigns, evaluation_scores,
                                 model_training_cases, model_versions,
                                 validation_cases)
from domain.readback import all_rows, one

LOSS_STR = tuple(str(segment) for segment in LOSS_SEGMENTS)


# ---------- 数据集 ----------

def _labeled_rows(conn):
    """已结案且人工归责的缺件段样本，附带其归责版本时间与同场婚宴。"""
    statement = (
        select(counts, issues.c.responsible_segment, issues.c.responsible_name,
               issues.c.label_revised_at, banquet_tables.c.party,
               banquet_tables.c.code.label('table_code'),
               placements.c.outbound_count, cases.c.capacity,
               cases.c.code.label('case_code'))
        .join(issues, issues.c.frame_code == counts.c.code)
        .join(placements, placements.c.code == counts.c.placement_code)
        .join(banquet_tables, banquet_tables.c.code == placements.c.table_code)
        .join(cases, cases.c.code == placements.c.case_code)
        .where(issues.c.state == IssueState.RESOLVED,
               issues.c.category == 'count_loss',
               issues.c.responsible_segment.in_(LOSS_STR)))
    rows = []
    for row in conn.execute(statement).mappings():
        features = {name: row[name] for name in learning.FEATURES[3:]}
        features.update({
            'outbound_delta': (row['capacity'] - row['outbound_count']) / row['capacity'],
            'table_delta': (row['outbound_count'] - row['table_count']) / row['capacity'],
            'return_delta': (row['table_count'] - row['return_count']) / row['capacity'],
        })
        rows.append({'case_code': row['case_code'], 'party': row['party'],
                     'label': row['responsible_segment'], 'features': features,
                     'label_revised_at': row['label_revised_at']})
    return rows


def _grouped_split(rows, rng_seed=7):
    """按婚宴（party）整组切分，同场婚宴的箱绝不跨训练/验收。"""
    parties = sorted({row['party'] for row in rows})
    rng = _SplitRandom(rng_seed)
    rng.shuffle(parties)
    # 预留约三分之一婚宴给验收，其余进训练。
    hold = max(1, len(parties) // 3)
    hold_parties = set(parties[:hold])
    train = [row for row in rows if row['party'] not in hold_parties]
    valid = [row for row in rows if row['party'] in hold_parties]
    return train, valid, hold_parties


class _SplitRandom:
    def __init__(self, seed):
        from random import Random
        self._rng = Random(seed)

    def shuffle(self, values):
        self._rng.shuffle(values)


def _assert_three_segments(rows, scope):
    present = {row['label'] if 'label' in row else row['truth_segment'] for row in rows}
    missing = [segment for segment in LOSS_STR if segment not in present]
    if missing:
        raise HTTPException(409, f'{scope}缺少缺件段样本：{"、".join(missing)}，'
                                 '三个缺件段（后场装箱/宴台清点/撤席回收）都要有样本')


# ---------- baseline 兜底 ----------

def ensure_baseline(conn):
    existing = conn.scalar(select(model_versions.c.code)
                           .where(model_versions.c.code == learning.BASELINE_VERSION))
    if existing:
        return
    _, metrics = learning.baseline_bundle()
    conn.execute(model_versions.insert().values(
        code=learning.BASELINE_VERSION, status=ModelStatus.ACTIVE,
        artifact_path=None, trained_on_cases=[], metrics=metrics,
        stale_label_cases=[], activated_at=now()))


def active_version(conn, lock=False):
    statement = select(model_versions).where(model_versions.c.status == ModelStatus.ACTIVE)
    if lock:
        statement = statement.with_for_update()
    row = conn.execute(statement).mappings().first()
    if row is None:
        raise HTTPException(409, '没有在用模型版本')
    return dict(row)


# ---------- 训练 ----------

def train_candidate(user):
    with transaction() as conn:
        ensure_baseline(conn)
        rows = _labeled_rows(conn)
        if len(rows) < 6:
            raise HTTPException(409, '已结案人工归责样本不足，至少需要 6 个缺件箱才能训练候选版')
        train, valid, hold_parties = _grouped_split(rows)
        _assert_three_segments(train, '训练集')
        _assert_three_segments(valid, '验收集')

        sequence = conn.scalar(select(func.count()).select_from(model_versions))
        version = f'candidate-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{sequence:02d}'
        model, metrics = learning.train_artifact(train)
        # 与 baseline 指标结构对齐，清点页统一读 holdout 条数。
        metrics['holdout'] = len(valid)
        metrics['holdout_parties'] = sorted(hold_parties)
        metrics['holdout_cases'] = [r['case_code'] for r in valid]
        path = learning.save_artifact(version, model, metrics)

        conn.execute(model_versions.insert().values(
            code=version, status=ModelStatus.TRAINING, artifact_path=path,
            trained_on_cases=[r['case_code'] for r in train], metrics=metrics,
            stale_label_cases=[]))
        for row in train:
            # label_segment 即训练时刻该箱人工归责的标签快照；
            # 评审上线时若归责在此之后被更正，则判定为带过期归责并拒绝。
            conn.execute(model_training_cases.insert().values(
                model_version=version, case_code=row['case_code'],
                label_segment=row['label']))
        record(conn, user, f'model-train:{version}:{len(train)}')
        return {'version': version, 'status': ModelStatus.TRAINING,
                'train_cases': len(train), 'validation_cases': len(valid),
                'validation_parties': sorted(hold_parties), 'metrics': metrics,
                'validation_rows': valid}


# ---------- 过关评审与一次性切换 ----------

def _persist_rejection(version, stale, user):
    """独立事务持久化拒绝状态，避免随主事务的 409 回滚而丢失。"""
    with transaction() as conn:
        conn.execute(model_versions.update()
                     .where(model_versions.c.code == version)
                     .values(status=ModelStatus.REJECTED, stale_label_cases=stale))
        record(conn, user, f'model-reject-stale:{version}')


def evaluate_and_promote(version, user):
    # 先在独立只读事务判定过期归责。不能在持 FOR UPDATE 锁的事务里再开事务更新同一行，
    # 否则在 PostgreSQL 上会等待自身持有的行锁，形成自死锁。
    with transaction() as conn:
        one(conn, model_versions, version)  # 版本不存在时给 404
        stale = _stale_since_training(conn, version)
    if stale:
        _persist_rejection(version, stale, user)
        raise HTTPException(409, '候选版带过期归责，拒绝上线：' + '、'.join(stale))

    with transaction() as conn:
        candidate = one(conn, model_versions, version, lock=True)
        if candidate['status'] not in (ModelStatus.TRAINING, ModelStatus.EVALUATED):
            raise HTTPException(409, '只有训练完成、尚未作废的候选版才能参加评审')

        rows = _labeled_rows(conn)
        _, valid, hold_parties = _grouped_split(rows)
        _assert_three_segments(valid, '验收集')
        for row in valid:
            row['truth_segment'] = row['label']
        incumbent = active_version(conn, lock=True)

        campaign_code = f'eval-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{version[-2:]}'
        conn.execute(evaluation_campaigns.insert().values(
            code=campaign_code, candidate_version=version,
            incumbent_version=incumbent['code'], decision='pending'))
        for row in valid:
            conn.execute(validation_cases.insert().values(
                campaign_code=campaign_code, case_code=row['case_code'],
                party=row['party'], truth_segment=row['label']))

        # 同一批评审验收箱，候选与在用版逐箱判别。
        candidate_miss, candidate_rows = learning.miss_report(version, valid)
        incumbent_miss, incumbent_rows = learning.miss_report(incumbent['code'], valid)
        for scored in (candidate_rows, incumbent_rows):
            for row in scored:
                conn.execute(evaluation_scores.insert().values(
                    campaign_code=campaign_code,
                    model_version=version if scored is candidate_rows else incumbent['code'],
                    **row))

        # 任一段候选漏判更多即不换版；相等或更少才过关。
        worse_segments = [segment for segment in LOSS_STR
                          if candidate_miss[segment] > incumbent_miss[segment]]
        report = {'campaign': campaign_code, 'validation_cases': len(valid),
                  'validation_parties': sorted(hold_parties),
                  'candidate_misses': candidate_miss, 'incumbent_misses': incumbent_miss,
                  'incumbent': incumbent['code']}
        if worse_segments:
            reason = '漏判更多的缺件段：' + '、'.join(worse_segments)
            conn.execute(evaluation_campaigns.update()
                         .where(evaluation_campaigns.c.code == campaign_code)
                         .values(decision='rejected', reason=reason))
            conn.execute(model_versions.update()
                         .where(model_versions.c.code == version)
                         .values(status=ModelStatus.REJECTED))
            record(conn, user, f'model-reject:{campaign_code}')
            report.update(decision='rejected', reason=reason)
            return report

        # 过关：一次性原子切换。旧在用版转 superseded，候选转 active。
        conn.execute(model_versions.update()
                     .where(model_versions.c.code == incumbent['code'])
                     .values(status=ModelStatus.SUPERSEDED))
        conn.execute(model_versions.update()
                     .where(model_versions.c.code == version)
                     .values(status=ModelStatus.ACTIVE, activated_at=now()))
        conn.execute(evaluation_campaigns.update()
                     .where(evaluation_campaigns.c.code == campaign_code)
                     .values(decision='promoted'))
        record(conn, user, f'model-promote:{version}:from:{incumbent["code"]}')
        report.update(decision='promoted', reason='三段漏判均不高于在用版，已一次性切换')
        return report


def _stale_since_training(conn, version):
    """候选训练所用样本里，归责在训练之后被更正的箱。"""
    trained_at = conn.scalar(select(model_versions.c.trained_at)
                             .where(model_versions.c.code == version))
    linked = select(model_training_cases.c.case_code).where(
        model_training_cases.c.model_version == version)
    revised = conn.execute(
        select(issues.c.case_code).where(
            issues.c.case_code.in_(linked),
            issues.c.label_revised_at.is_not(None),
            issues.c.label_revised_at > trained_at)).mappings().all()
    return sorted({row['case_code'] for row in revised})


# ---------- 归责更正：作废与回退 ----------

def revise_attribution(issue_code, form, user):
    with transaction() as conn:
        issue = one(conn, issues, issue_code, lock=True)
        if issue['state'] != IssueState.RESOLVED:
            raise HTTPException(409, '只有已结案归责才能更正')
        if issue['category'] != 'count_loss':
            raise HTTPException(409, '撞码差错没有缺件归责可更正')
        if form.segment == Segment.BALANCED:
            raise HTTPException(409, '缺件归责须指定一个实际交接段')
        if form.segment == issue['responsible_segment']:
            raise HTTPException(409, '更正后的责任段与原归责相同，无需更正')

        stamp = now()
        conn.execute(issues.update().where(issues.c.code == issue_code).values(
            responsible_segment=form.segment, responsible_name=form.person,
            label_revised_at=stamp))

        # 用过该箱旧归责的所有版本作废（baseline 不依赖人工归责，不在其中）。
        affected = [row[0] for row in conn.execute(
            select(model_training_cases.c.model_version).where(
                model_training_cases.c.case_code == issue['case_code'])).all()]
        invalidated = []
        for model_code in sorted(set(affected)):
            target = one(conn, model_versions, model_code, lock=True)
            if target['status'] in (ModelStatus.REJECTED, ModelStatus.INVALID):
                continue
            conn.execute(model_versions.update()
                         .where(model_versions.c.code == model_code)
                         .values(status=ModelStatus.INVALID, invalidated_at=stamp))
            invalidated.append(model_code)

        rollback = None
        still_active = conn.execute(
            select(model_versions.c.code).where(
                model_versions.c.status == ModelStatus.ACTIVE)).mappings().first()
        if still_active is None:
            # 在用版被作废：退回最近一个“曾在用且未依赖被更正标签”的有效版。
            # 依赖该箱旧归责的版本上面都已置 invalid，故剩下的 superseded 版可安全接管；
            # 从未通过评审的 training/evaluated 候选不算有效版，不能绕过过关闸门。
            fallback = conn.execute(
                select(model_versions).where(
                    model_versions.c.status == ModelStatus.SUPERSEDED)
                .order_by(model_versions.c.activated_at.desc().nullslast())
                .limit(1)).mappings().first()
            if fallback is None:
                # 没有可接管的历史在用版时，由永不作废的 baseline 兜底。
                one(conn, model_versions, learning.BASELINE_VERSION, lock=True)
                conn.execute(model_versions.update()
                             .where(model_versions.c.code == learning.BASELINE_VERSION)
                             .values(status=ModelStatus.ACTIVE, activated_at=stamp))
                rollback = learning.BASELINE_VERSION
            else:
                conn.execute(model_versions.update()
                             .where(model_versions.c.code == fallback['code'])
                             .values(status=ModelStatus.ACTIVE, activated_at=stamp))
                rollback = fallback['code']

        record(conn, user, f'label-revise:{issue_code}:{form.segment}:invalidate:'
                          + ','.join(invalidated) + f':rollback:{rollback}')
        return {'issue': issue_code, 'segment': form.segment,
                'invalidated_versions': invalidated, 'active_version': rollback}


# ---------- 读模型 ----------

def governance_overview():
    with transaction() as conn:
        ensure_baseline(conn)
        versions = all_rows(conn, model_versions)
        campaigns = all_rows(conn, evaluation_campaigns)
        active = active_version(conn)
        return {'active_version': active['code'], 'versions': versions, 'campaigns': campaigns}
