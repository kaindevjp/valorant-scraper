import json
from pathlib import Path

import jsonschema

from .logger import get_logger
from .models import MatchData, MATCH_SCHEMA

logger = get_logger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def should_skip(match_id: str) -> bool:
    return (OUTPUT_DIR / f"{match_id}.json").exists()


def save(match: MatchData) -> Path:
    data = match.to_dict()

    try:
        jsonschema.validate(data, MATCH_SCHEMA)
    except jsonschema.ValidationError as e:
        logger.error("Schema validation failed for %s: %s", match.match_id, e.message)
        raise

    path = OUTPUT_DIR / f"{match.match_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %s", path)
    return path
