from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    question: str
    premises: list[str] = []  # Empty list for Type 2 queries


class QueryResponse(BaseModel):
    answer: str
    explanation: str
    fol: Optional[str] = None
    cot: Optional[list[str]] = None
    premises: Optional[list[str]] = None
    confidence: Optional[float] = None
