"""
Usage:
  python main.py --url "https://www.thespike.gg/jp/match/.../143054"
  python main.py --match-ids 143054 143055 143056
  python main.py --event-id 4043
  python main.py --event-id 4043 --all          # 未開催も含む
  python main.py --event-id 4043 --force        # 既存ファイルを上書き
"""

import argparse
import re
import time

from tqdm import tqdm

from scraper import api_client, storage
from scraper.logger import get_logger

logger = get_logger(__name__)

REQUEST_INTERVAL = 3.0


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


def _run_batch(match_ids: list[str], force: bool) -> None:
    errors: list[tuple[str, str]] = []
    skipped = 0

    for i, match_id in enumerate(tqdm(match_ids, desc="取得中", unit="試合")):
        try:
            processed = _process(match_id, force)
            if not processed:
                skipped += 1
            elif i < len(match_ids) - 1:
                time.sleep(REQUEST_INTERVAL)
        except ValueError as e:
            logger.error("match %s: %s", match_id, e)
            errors.append((match_id, str(e)))
        except Exception as e:
            logger.error("match %s: unexpected error: %s", match_id, e)
            errors.append((match_id, str(e)))

    fetched = len(match_ids) - len(errors) - skipped
    print(f"\n完了: {fetched}件取得 / {skipped}件スキップ / {len(errors)}件エラー  (合計{len(match_ids)}件)")
    if errors:
        print("エラー一覧:")
        for mid, msg in errors:
            print(f"  {mid}: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="thespike.gg 試合データ取得ツール")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="試合ページの URL（1試合）")
    group.add_argument("--match-ids", nargs="+", metavar="ID", help="試合 ID（複数指定可）")
    group.add_argument("--event-id", metavar="ID", help="イベント ID（例: 4043）")
    parser.add_argument("--all", action="store_true", help="未開催試合も対象にする（--event-id と併用）")
    parser.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    args = parser.parse_args()

    if args.url:
        match_ids = [_extract_match_id(args.url)]
    elif args.match_ids:
        match_ids = args.match_ids
    else:
        finished_only = not args.all
        match_ids = api_client.fetch_event_match_ids(args.event_id, finished_only=finished_only)
        if not match_ids:
            print("対象の試合が見つかりませんでした。")
            return

    _run_batch(match_ids, args.force)


if __name__ == "__main__":
    main()
