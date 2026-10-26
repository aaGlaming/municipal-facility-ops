import hashlib
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_tree_with_manifest(source: Path, target: Path) -> dict[str, object]:
    source = source.resolve()
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    source_files = {path.relative_to(source) for path in source.rglob("*") if path.is_file()}
    for relative in source_files:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    target_files = {path.relative_to(target) for path in target.rglob("*") if path.is_file()}
    mismatches = [
        str(relative)
        for relative in sorted(source_files | target_files)
        if relative not in source_files
        or relative not in target_files
        or _sha256(source / relative) != _sha256(target / relative)
    ]
    return {"copied_files": len(source_files), "target_files": len(target_files), "mismatches": mismatches}


if __name__ == "__main__":
    print(copy_tree_with_manifest(Path("data"), Path("../data/municipal-facility-ops")))
