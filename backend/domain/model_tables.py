from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Table, UniqueConstraint

from core.db import metadata
from domain.evidence_tables import now

# 分段模型版本登记。baseline 是系统自带模拟版，永不作废，作为回退兜底。
model_versions = Table(
    'segment_model_versions', metadata,
    Column('code', String(40), primary_key=True),
    Column('status', String(12), nullable=False),
    Column('artifact_path', String(220)),
    Column('trained_on_cases', JSON, nullable=False),
    Column('metrics', JSON, nullable=False),
    Column('stale_label_cases', JSON, nullable=False),
    Column('trained_at', DateTime, nullable=False, default=now),
    Column('activated_at', DateTime),
    Column('invalidated_at', DateTime),
    CheckConstraint("status IN ('training','evaluated','active','superseded','rejected','invalid')"),
)

# 一次过关评审对应一整批评审验收箱；同一次评审里候选与在用版用完全相同的验收箱。
evaluation_campaigns = Table(
    'model_evaluation_campaigns', metadata,
    Column('code', String(40), primary_key=True),
    Column('candidate_version', String(40), ForeignKey('segment_model_versions.code'), nullable=False),
    Column('incumbent_version', String(40), ForeignKey('segment_model_versions.code'), nullable=False),
    Column('created_at', DateTime, nullable=False, default=now),
    Column('decision', String(12), nullable=False, default='pending'),
    Column('reason', String(220)),
    CheckConstraint("decision IN ('pending','promoted','rejected')"),
)

# 验收箱按婚宴（party）整组进入，不与训练箱同场。
validation_cases = Table(
    'model_validation_cases', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('campaign_code', String(40), ForeignKey('model_evaluation_campaigns.code'), nullable=False),
    Column('case_code', String(22), ForeignKey('lidded_cases.code'), nullable=False),
    Column('party', String(48), nullable=False),
    Column('truth_segment', String(18), nullable=False),
    UniqueConstraint('campaign_code', 'case_code'),
)

# 候选与在用版在同一验收箱上的逐箱判别，用于逐段统计漏判。
evaluation_scores = Table(
    'model_evaluation_scores', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('campaign_code', String(40), ForeignKey('model_evaluation_campaigns.code'), nullable=False),
    Column('model_version', String(40), ForeignKey('segment_model_versions.code'), nullable=False),
    Column('case_code', String(22), ForeignKey('lidded_cases.code'), nullable=False),
    Column('predicted_segment', String(18), nullable=False),
    Column('truth_segment', String(18), nullable=False),
    Column('missed', Integer, nullable=False),
    UniqueConstraint('campaign_code', 'model_version', 'case_code'),
)

# 版本训练时实际学习过的人工归责样本；归责被更正时据此定位作废版本。
model_training_cases = Table(
    'model_training_cases', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('model_version', String(40), ForeignKey('segment_model_versions.code'), nullable=False),
    Column('case_code', String(22), ForeignKey('lidded_cases.code'), nullable=False),
    Column('label_segment', String(18), nullable=False),
    UniqueConstraint('model_version', 'case_code'),
)
