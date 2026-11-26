from enum import StrEnum


class TableState(StrEnum):
    ARRANGED = 'arranged'
    CLEARED = 'cleared'


class CaseState(StrEnum):
    STAGED = 'staged'
    AT_TABLE = 'at_table'
    LOCKED = 'locked'
    CLOSED = 'closed'


class Segment(StrEnum):
    OUTBOUND = 'outbound'
    TABLE = 'table'
    COLLECTION = 'collection'
    BALANCED = 'balanced'


class IssueState(StrEnum):
    OPEN = 'open'
    ASSIGNED = 'assigned'
    RESOLVED = 'resolved'


class ModelStatus(StrEnum):
    TRAINING = 'training'      # 训练完成、尚未参加过关评审
    EVALUATED = 'evaluated'    # 已在固定验收箱上与在用版对比
    ACTIVE = 'active'          # 当前给新单使用的唯一版本
    SUPERSEDED = 'superseded'  # 曾在用、已被新版替换
    REJECTED = 'rejected'      # 验收不过或带过期归责，拒绝上线
    INVALID = 'invalid'        # 依赖的人工归责被更正，版本作废


LOSS_SEGMENTS = (Segment.OUTBOUND, Segment.TABLE, Segment.COLLECTION)
