from pathlib import Path

from app.chunking.filters import should_skip_dir, should_skip_file
from app.services.ingest import _collect_files


def test_skips_dependency_and_cache_directories() -> None:
    assert should_skip_dir("node_modules")
    assert should_skip_dir("__pycache__")
    assert should_skip_dir(".git")
    assert not should_skip_dir("app")


def test_skips_lockfiles_binaries_and_huge_files(tmp_path: Path) -> None:
    lock = tmp_path / "package-lock.json"
    lock.write_text("{}")
    huge = tmp_path / "app.py"
    huge.write_bytes(b"x" * (201 * 1024))
    binary = tmp_path / "photo.png"
    binary.write_bytes(b"\x00\x01")
    ok = tmp_path / "auth.py"
    ok.write_text("x = 1\n")

    assert should_skip_file(lock, lock.stat().st_size)
    assert should_skip_file(huge, huge.stat().st_size)
    assert should_skip_file(binary, binary.stat().st_size)
    assert not should_skip_file(ok, ok.stat().st_size)


def test_collect_files_ignores_nested_node_modules(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "main.py").write_text("print(1)\n")
    nested = tmp_path / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "index.js").write_text("module.exports = 1\n")

    selected, skipped = _collect_files(tmp_path)
    paths = {path.relative_to(tmp_path).as_posix() for path in selected}
    assert "app/main.py" in paths
    assert "node_modules/pkg/index.js" not in paths
    assert skipped >= 1
