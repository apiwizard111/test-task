from app.api.sources import build_tree
from app.models.manifest import FileEntry


def test_build_tree_folders_first_and_nested() -> None:
    tree = build_tree(
        [
            FileEntry(path="README.md", language="markdown", bytes=10, lines=2),
            FileEntry(path="tests/test_auth.py", language="python", bytes=10, lines=2),
            FileEntry(path="src/app/core/auth.py", language="python", bytes=10, lines=2),
            FileEntry(path="src/app/api/routes.py", language="python", bytes=10, lines=2),
            FileEntry(path="app.py", language="python", bytes=10, lines=2),
        ]
    )

    assert [node["name"] for node in tree] == ["src", "tests", "app.py", "README.md"]
    src = tree[0]
    assert src["kind"] == "dir"
    assert src["children"][0]["name"] == "app"
    app = src["children"][0]
    assert [child["name"] for child in app["children"]] == ["api", "core"]


def test_build_tree_normalizes_windows_separators() -> None:
    tree = build_tree(
        [FileEntry(path="pkg\\module\\main.py", language="python", bytes=10, lines=2)]
    )
    assert tree[0]["name"] == "pkg"
    assert tree[0]["children"][0]["name"] == "module"
    assert tree[0]["children"][0]["children"][0]["path"] == "pkg/module/main.py"
