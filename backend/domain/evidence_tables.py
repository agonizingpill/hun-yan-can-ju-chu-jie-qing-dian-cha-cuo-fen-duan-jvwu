from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table
from core.db import metadata

counts = Table(
    'count_frames',metadata,
    Column('code',String(22),primary_key=True),
    Column('placement_code',String(22),ForeignKey('table_case_placements.code'),nullable=False,unique=True),
    Column('table_count',Integer,nullable=False),
    Column('return_count',Integer,nullable=False),
    Column('covered_ratio',Float,nullable=False),
    Column('blur_share',Float,nullable=False),
    Column('edge_overlap',Float,nullable=False),
    Column('handoff_gap',Float,nullable=False),
    Column('model_segment',String(18),nullable=False),
    Column('model_version',String(40),nullable=False),
    Column('votes',JSON,nullable=False),
    Column('missing',Integer,nullable=False),
    Column('compute_token',String(32),nullable=False,unique=True),
    Column('signed_by',String(80),nullable=False),
    CheckConstraint('table_count >= 0 AND return_count >= 0 AND missing >= 0'),
)

issues = Table(
    'custody_discrepancies',metadata,
    Column('code',String(26),primary_key=True),
    Column('case_code',String(22),ForeignKey('lidded_cases.code'),nullable=False),
    Column('placement_code',String(22),ForeignKey('table_case_placements.code'),nullable=False),
    Column('frame_code',String(22),ForeignKey('count_frames.code'),unique=True),
    Column('conflicting_table',String(22),ForeignKey('banquet_tables.code')),
    Column('category',String(16),nullable=False),
    Column('state',String(16),nullable=False,default='open'),
    Column('responsible_segment',String(18)),
    Column('responsible_name',String(48)),
    Column('released_count',Integer),
    Column('resolved_by',String(80)),
    Column('label_revised_at',DateTime),
    CheckConstraint("category IN ('label_conflict','count_loss')"),
    CheckConstraint("state IN ('open','assigned','resolved')"),
    CheckConstraint("(frame_code IS NULL AND conflicting_table IS NOT NULL) OR "
                    "(frame_code IS NOT NULL AND conflicting_table IS NULL)"),
)


def now():
    return datetime.now(timezone.utc)
