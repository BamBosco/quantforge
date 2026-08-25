"""Dataset identity and exclusion controls for reproducible research runs."""

import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Immutable metadata needed to identify one historical data export."""

    dataset_id: str
    instrument: str
    sha256: str
    source_timezone: str
    start_utc: datetime
    end_utc: datetime
    excluded_session_days: frozenset[date]


def load_dataset_manifest(path: Path) -> DatasetManifest:
    """Load one dataset manifest and reject malformed research metadata."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    try:
        identity = raw["identity"]
        time = raw["time"]
        excluded_days = frozenset(
            date.fromisoformat(value)
            for value in raw["quality"]["excluded_session_days"]
        )
        manifest = DatasetManifest(
            dataset_id=str(identity["dataset_id"]),
            instrument=str(identity["instrument"]),
            sha256=str(identity["sha256"]),
            source_timezone=str(time["source_timezone"]),
            start_utc=datetime.fromisoformat(str(time["start_utc"])),
            end_utc=datetime.fromisoformat(str(time["end_utc"])),
            excluded_session_days=excluded_days,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid dataset manifest") from error
    if not manifest.dataset_id or not manifest.instrument:
        raise ValueError("dataset manifest identity must not be empty")
    if len(manifest.sha256) != 64:
        raise ValueError("dataset manifest requires a SHA-256 checksum")
    if manifest.start_utc.tzinfo is None or manifest.end_utc.tzinfo is None:
        raise ValueError("dataset manifest timestamps must be timezone-aware")
    if manifest.start_utc >= manifest.end_utc:
        raise ValueError("dataset manifest range must be ordered")
    return manifest


def verify_dataset_checksum(path: Path, manifest: DatasetManifest) -> None:
    """Reject a data file whose contents differ from the audited manifest."""
    digest = sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != manifest.sha256:
        raise ValueError("dataset checksum does not match the approved manifest")
