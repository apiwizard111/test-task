import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.github import parse_github_url


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_before_ingest(client: TestClient) -> None:
    response = client.get("/api/ready")
    body = response.json()
    assert body["ingested"] is False
    assert body["llm_configured"] is True


def test_chat_requires_ingest(client: TestClient) -> None:
    response = client.post("/api/chat/stream", json={"message": "How does auth work?", "history": []})
    assert response.status_code == 409


def test_ingest_sample_and_chat(client: TestClient) -> None:
    ingest = client.post("/api/ingest/sample")
    assert ingest.status_code == 200, ingest.text
    payload = ingest.json()
    assert payload["file_count"] >= 6
    assert payload["chunk_count"] >= 6
    assert payload["name"] == "nexus-tasks"

    sources = client.get("/api/sources")
    tree = sources.json()
    assert tree["ingested"] is True
    assert any(node["name"] == "app" for node in tree["tree"])

    content = client.get("/api/sources/content", params={"path": "app/auth.py"})
    assert content.status_code == 200
    assert "X-API-Key" in content.json()["content"]

    chat = client.post("/api/chat/stream", json={"message": "How does authentication work?", "history": []})
    assert chat.status_code == 200
    body = chat.text
    assert "X-API-Key" in body or "Authentication" in body
    assert "event: done" in body


def test_ingest_zip(client: TestClient, tmp_path: Path) -> None:
    archive = tmp_path / "tiny.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("tiny/hello.py", "def ping():\n    return 'pong'\n")
        zipped.writestr("tiny/node_modules/skip.js", "console.log(1)\n")
    ingest = client.post(
        "/api/ingest/zip",
        files={"file": ("tiny.zip", archive.read_bytes(), "application/zip")},
    )
    assert ingest.status_code == 200, ingest.text
    sources = client.get("/api/sources").json()
    paths = _flatten_files(sources["tree"])
    assert "tiny/hello.py" in paths or "hello.py" in paths
    assert not any("node_modules" in path for path in paths)


def test_parse_github_urls() -> None:
    parsed = parse_github_url("https://github.com/pallets/flask")
    assert parsed.owner == "pallets"
    assert parsed.repo == "flask"
    nested = parse_github_url("https://github.com/pallets/flask/tree/2.3.x")
    assert nested.branch == "2.3.x"


def _flatten_files(nodes: list[dict]) -> list[str]:
    paths: list[str] = []
    for node in nodes:
        if node["kind"] == "file":
            paths.append(node["path"])
        paths.extend(_flatten_files(node["children"]))
    return paths
