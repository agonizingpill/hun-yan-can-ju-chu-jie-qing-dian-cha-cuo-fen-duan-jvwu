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
