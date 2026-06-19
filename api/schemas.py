from pydantic import BaseModel
from typing import Optional, Literal


class UnifiedRequest(BaseModel):
    query_id: str
    type: Literal["type1", "type2"]
    query: str
    premises: list[str] = []
    options: list[str] = []
    logs: Optional[bool] = None


class ReasoningBlock(BaseModel):
    type: Literal["fol", "cot", "proof"]
    steps: list[str]


class UnifiedResponse(BaseModel):
    query_id: str
    answer: str
    unit: str
    explanation: str
    premises_used: list[int]
    reasoning: Optional[ReasoningBlock] = None
    logs: Optional[list[str]] = None

