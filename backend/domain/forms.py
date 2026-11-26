from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from domain.labels import Segment

Code = Annotated[str,StringConstraints(strip_whitespace=True,pattern=r'^[A-Z0-9][A-Z0-9-]{2,21}$')]
Count = Annotated[int,Field(ge=0,le=36)]
Ratio = Annotated[float,Field(ge=0,le=1,allow_inf_nan=False)]


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Place(Input):
    code: Code
    case_code: Code
    table_code: Code
    lid_tag: Code
    outbound_count: Count


class CountFrame(Input):
    placement_code: Code
    table_count: Count
    return_count: Count
    covered_ratio: Ratio
    blur_share: Ratio
    edge_overlap: Ratio
    handoff_gap: Ratio


class Signature(Input):
    code: Code
    token: Annotated[str,StringConstraints(pattern=r'^[0-9a-f]{32}$')]


class Custody(Input):
    segment: Segment
    person: Annotated[str,StringConstraints(strip_whitespace=True,min_length=2,max_length=48)]


class Inspection(Input):
    correctly_labeled_table: Code
    witnessed_tag: Code
    counted: Count


class Revision(Input):
    segment: Segment
    person: Annotated[str,StringConstraints(strip_whitespace=True,min_length=2,max_length=48)]
