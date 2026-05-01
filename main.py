"""
Usage:
  python main.py --url  "https://www.thespike.gg/jp/match/.../143054"
  python main.py --match-ids 143054 143055 143056
  python main.py --match-ids 143054 --force
"""

import argparse
import re
import time

from tqdm import tqdm

from scraper import api_client, storage
from scraper.logger import get_logger

logger = get_logger(__name__)

REQUEST_INTERVAL = 3.0  # 試合間の待機秒数


def _extract_match_id(url: str) -> str:
    m = re.search(r"/(\d+)(?:[/?#]|$)", url)
    if not m:
        raise ValueError(f"URL から match_id を抽出できません: {url}")
    return m.group(1)


def _process(match_id: str, force: bool) -> bool:
    """1試合を取得して保存。スキップした場合は False を返す。"""
    if not force and storage.should_skip(match_id):
        logger.info("Skip %s (already exists)", match_id)
        return False

    match = api_client.fetch(match_id)
    storage.save(match)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="thespike.gg 試合データ取得ツール")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="試合ページの URL")
    group.add_argument("--match-ids", nargs="+", metavar="ID", help="試合 ID（複数指定可）")
    parser.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    args = parser.parse_args()

    if args.url:
        match_ids = [_extract_match_id(args.url)]
    else:
        match_ids = args.match_ids

    errors: list[tuple[str, str]] = []

    for i, match_id in enumerate(tqdm(match_ids, desc="取得中", unit="試合")):
        try:
            processed = _process(match_id, args.force)
            if processed and i < len(match_ids) - 1:
                time.sleep(REQUEST_INTERVAL)
        except ValueError as e:
            # 404 など回復不能なエラー
            logger.error("match %s: %s", match_id, e)
            errors.append((match_id, str(e)))
        except Exception as e:
            logger.error("match %s: unexpected error: %s", match_id, e)
            errors.append((match_id, str(e)))

    print(f"\n完了: {len(match_ids) - len(errors)}/{len(match_ids)} 件取得")
    if errors:
        print("エラー:")
        for mid, msg in errors:
            print(f"  {mid}: {msg}")


if __name__ == "__main__":
    main()
