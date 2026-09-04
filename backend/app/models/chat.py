from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list, max_length=20)


class GithubIngestRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    path: str
    symbol: str
    start_line: int
    end_line: int


class RetrievedChunk(BaseModel):
    path: str
    symbol: str
    start_line: int
    end_line: int
    score: float
