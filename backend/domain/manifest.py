from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from core.db import metadata

banquet_tables = Table(
    'banquet_tables', metadata,
    Column('code',String(22),primary_key=True),
    Column('hall',String(48),nullable=False),
    Column('party',String(48),nullable=False),
    Column('seats',Integer,nullable=False),
    Column('course',String(40),nullable=False),
    Column('runner',String(48),nullable=False),
    Column('state',String(16),nullable=False,default='arranged'),
    CheckConstraint('seats BETWEEN 2 AND 24'),
    CheckConstraint("state IN ('arranged','cleared')"),
)

cases = Table(
    'lidded_cases', metadata,
    Column('code',String(22),primary_key=True),
    Column('dish',String(52),nullable=False),
    Column('capacity',Integer,nullable=False),
    Column('lid_tag',String(22),nullable=False,unique=True),
    Column('state',String(16),nullable=False,default='staged'),
    CheckConstraint('capacity BETWEEN 2 AND 36'),
    CheckConstraint("state IN ('staged','at_table','locked','closed')"),
)

placements = Table(
    'table_case_placements',metadata,
    Column('code',String(22),primary_key=True),
    Column('table_code',String(22),ForeignKey('banquet_tables.code'),nullable=False),
    Column('case_code',String(22),ForeignKey('lidded_cases.code'),nullable=False,unique=True),
    Column('outbound_count',Integer,nullable=False),
    Column('counted_by',String(80),nullable=False),
    UniqueConstraint('table_code','case_code'),
    CheckConstraint('outbound_count > 0'),
)
