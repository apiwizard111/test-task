from pathlib import Path

from app.models.chunk import CodeChunk
from app.services.retrieve import reciprocal_rank_fusion


def _chunk(symbol: str) -> CodeChunk:
    return CodeChunk(
        id=symbol,
        path=f"{symbol}.py",
        language="python",
        symbol=symbol,
        start_line=1,
        end_line=2,
        text=f"def {symbol}():\n    return 1",
    )


def test_rrf_boosts_chunks_that_appear_in_both_lists() -> None:
    auth = _chunk("authenticate")
    tasks = _chunk("list_tasks")
    health = _chunk("health")
    fused = reciprocal_rank_fusion([[tasks, auth], [tasks, health]])
    assert fused[0].chunk.id == "list_tasks"
    assert fused[0].score > fused[1].score


def test_rrf_keeps_unique_vector_hits() -> None:
    auth = _chunk("authenticate")
    health = _chunk("health")
    fused = reciprocal_rank_fusion([[auth], [health]])
    ids = {item.chunk.id for item in fused}
    assert ids == {"authenticate", "health"}
