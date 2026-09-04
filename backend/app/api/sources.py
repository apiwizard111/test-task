from fastapi import APIRouter, HTTPException, Query, Request

from app.models.manifest import FileEntry
from app.services.store import Store

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(request: Request) -> dict:
    store: Store = request.app.state.store
    if store.manifest is None:
        return {"ingested": False, "name": "", "file_count": 0, "chunk_count": 0, "tree": []}
    return {
        "ingested": True,
        "name": store.manifest.name,
        "source": store.manifest.source,
        "file_count": store.manifest.file_count,
        "chunk_count": store.manifest.chunk_count,
        "tree": build_tree(store.manifest.files),
    }


@router.get("/content")
def file_content(request: Request, path: str = Query(min_length=1, max_length=400)) -> dict:
    store: Store = request.app.state.store
    try:
        content = store.read_source(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return {"path": path, "content": content}


def build_tree(files: list[FileEntry]) -> list[dict]:
    root: dict[str, dict] = {}
    for entry in files:
        parts = [part for part in entry.path.replace("\\", "/").split("/") if part and part != "."]
        if not parts:
            continue
        cursor = root
        trail: list[str] = []
        for index, part in enumerate(parts):
            trail.append(part)
            is_file = index == len(parts) - 1
            node = cursor.setdefault(
                part,
                {
                    "name": part,
                    "path": "/".join(trail),
                    "kind": "file" if is_file else "dir",
                    "language": entry.language if is_file else None,
                    "children": {},
                },
            )
            if is_file:
                node["kind"] = "file"
                node["language"] = entry.language
            elif node["kind"] != "file":
                node["kind"] = "dir"
            cursor = node["children"]
    return _freeze(root)


def _freeze(nodes: dict[str, dict]) -> list[dict]:
    frozen: list[dict] = []
    for name in sorted(nodes, key=str.lower):
        node = nodes[name]
        children = _freeze(node["children"])
        frozen.append(
            {
                "name": node["name"],
                "path": node["path"],
                "kind": node["kind"],
                "language": node["language"],
                "children": children,
            }
        )
    frozen.sort(key=lambda item: (0 if item["kind"] == "dir" else 1, item["name"].lower()))
    return frozen
