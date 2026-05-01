import time

import httpx

from .logger import get_logger
from .models import (
    HeadToHead,
    MapResult,
    MatchData,
    Performance,
    PlayerStats,
    RoundEconomy,
)

logger = get_logger(__name__)

BASE_URL = "https://api.thespike.gg"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.thespike.gg/",
}
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _get(client: httpx.Client, url: str) -> dict:
    last_exc: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, 1):
        try:
            r = client.get(url, timeout=15)
            if r.status_code == 404:
                raise ValueError(f"Not found: {url}")
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", delay))
                logger.warning("Rate limited. Waiting %ds", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except ValueError:
            raise
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                logger.warning(
                    "Request failed (attempt %d/%d): %s — retrying in %ds",
                    attempt, MAX_RETRIES, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error("Request failed after %d attempts: %s", MAX_RETRIES, e)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 公開インターフェース
# ---------------------------------------------------------------------------

def fetch(match_id: str) -> MatchData:
    with httpx.Client(headers=HEADERS) as client:
        logger.info("Fetching match %s ...", match_id)
        match_raw = _get(client, f"{BASE_URL}/match/{match_id}")
        stats_raw = _get(client, f"{BASE_URL}/match/{match_id}/stats")
    return _parse(match_id, match_raw, stats_raw)


# ---------------------------------------------------------------------------
# パース
# ---------------------------------------------------------------------------

def _parse(match_id: str, match_raw: dict, stats_raw: dict) -> MatchData:
    teams = match_raw["teams"]

    # 選手ID -> {nickname, team_name, team_id}
    player_lookup: dict[int, dict] = {}
    for team in teams:
        for p in team["players"]:
            player_lookup[p["id"]] = {
                "nickname": p["nickname"],
                "team_name": team["title"],
                "team_id": team["id"],
            }

    # チームID -> チーム名
    team_lookup: dict[int, str] = {t["id"]: t["title"] for t in teams}

    # マップID -> マップ名
    map_name_lookup: dict[int, str] = {
        m["id"]: m["title"] for m in stats_raw["maps"]
    }

    url = (
        f"https://www.thespike.gg/jp/match/"
        f"{teams[0]['slug']}-{teams[1]['slug']}/{match_id}"
    )

    return MatchData(
        match_id=str(match_id),
        url=url,
        team1_id=teams[0]["id"],
        team1=teams[0]["title"],
        team1_score=teams[0]["score"],
        team2_id=teams[1]["id"],
        team2=teams[1]["title"],
        team2_score=teams[1]["score"],
        date=match_raw.get("startTime", ""),
        tournament=match_raw.get("event", {}).get("title", ""),
        maps=_parse_maps(stats_raw["maps"], teams),
        player_stats=_parse_player_stats(stats_raw, player_lookup, map_name_lookup),
        head_to_head=_parse_head_to_head(
            stats_raw["killMatrix"],
            stats_raw["allMaps"].get("killMatrix", {}),
            player_lookup,
            map_name_lookup,
        ),
        performances=_parse_performances(stats_raw, player_lookup, map_name_lookup),
        round_economy=_parse_round_economy(
            stats_raw["roundEconomy"], map_name_lookup, team_lookup
        ),
    )


def _parse_maps(maps_raw: list, teams: list) -> list[MapResult]:
    results = []
    for m in maps_raw:
        scores = m.get("scores", [])
        if len(scores) < 2:
            continue
        # scores は [team_a, team_b] の順（win フラグで勝者を特定）
        winner = next((s["teamName"] for s in scores if s["win"]), "")
        results.append(
            MapResult(
                map_id=m["id"],
                map_name=m["title"],
                team1_id=scores[0]["teamId"],
                team1_name=scores[0]["teamName"],
                team1_rounds=scores[0]["score"],
                team2_id=scores[1]["teamId"],
                team2_name=scores[1]["teamName"],
                team2_rounds=scores[1]["score"],
                winner=winner,
            )
        )
    return results


def _build_player_stat(p: dict, map_label: str, player_lookup: dict) -> PlayerStats | None:
    pid = p.get("playerId")
    if pid is None:
        return None
    info = player_lookup.get(pid, {})
    kills = p.get("kills", 0)
    deaths = p.get("deaths", 0)
    return PlayerStats(
        player_id=pid,
        player_name=p.get("nickname") or info.get("nickname", ""),
        team_id=p.get("teamId") or info.get("team_id", 0),
        team_name=info.get("team_name", ""),
        map=map_label,
        rating=float(p.get("playerRating", 0)),
        acs=float(p.get("averageCombatScore", 0)),
        kills=kills,
        deaths=deaths,
        assists=p.get("assists", 0),
        plus_minus=kills - deaths,
        kd=float(p.get("kdRatio", 0)),
        kast=float(p.get("kastPercentageTotal", 0)),
        adr=float(p.get("averageDamagePerRound", 0)),
        hs_pct=float(p.get("headshotPercentage", 0)),
        fbsr=float(p.get("firstBloodSuccessRate", 0)),
        fb=p.get("firstBloods", 0),
        fd=p.get("firstDeaths", 0),
        econ_rating=float(p.get("econRating", 0)),
        total_spent=p.get("totalSpent", 0),
    )


def _parse_player_stats(
    stats_raw: dict,
    player_lookup: dict,
    map_name_lookup: dict,
) -> list[PlayerStats]:
    results = []

    # 全マップ合算
    for p in stats_raw["allMaps"].get("players", []):
        stat = _build_player_stat(p, "all", player_lookup)
        if stat:
            results.append(stat)

    # マップ別
    for m in stats_raw["maps"]:
        map_label = map_name_lookup.get(m["id"], str(m["id"]))
        for p in m.get("players", []):
            stat = _build_player_stat(p, map_label, player_lookup)
            if stat:
                results.append(stat)

    return results


def _parse_head_to_head(
    per_map_matrix: dict,
    all_maps_matrix: dict,
    player_lookup: dict,
    map_name_lookup: dict,
) -> list[HeadToHead]:
    results = []

    def _extract(matrix: dict, map_id: int, map_name: str) -> None:
        for attacker_id_str, data in matrix.items():
            attacker_id = int(attacker_id_str)
            kills_map = data.get("kills", {})
            for victim_id_str, kill_count in kills_map.items():
                victim_id = int(victim_id_str)
                attacker_info = player_lookup.get(attacker_id, {})
                victim_info = player_lookup.get(victim_id, {})
                results.append(
                    HeadToHead(
                        map_id=map_id,
                        map_name=map_name,
                        attacker_id=attacker_id,
                        attacker_name=attacker_info.get("nickname", str(attacker_id)),
                        victim_id=victim_id,
                        victim_name=victim_info.get("nickname", str(victim_id)),
                        kills=kill_count,
                    )
                )

    # マップ別
    for map_id_str, matrix in per_map_matrix.items():
        map_id = int(map_id_str)
        map_name = map_name_lookup.get(map_id, map_id_str)
        _extract(matrix, map_id, map_name)

    # 全マップ合算（map_id=0 を慣例として使用）
    if all_maps_matrix:
        _extract(all_maps_matrix, 0, "all")

    return results


def _build_performance(p: dict, map_label: str, player_lookup: dict) -> Performance | None:
    pid = p.get("playerId")
    if pid is None:
        return None
    info = player_lookup.get(pid, {})
    return Performance(
        player_id=pid,
        player_name=p.get("nickname") or info.get("nickname", ""),
        team_name=info.get("team_name", ""),
        map=map_label,
        k2=p.get("multikillsBy2", 0),
        k3=p.get("multikillsBy3", 0),
        k4=p.get("multikillsBy4", 0),
        k5=p.get("multikillsBy5", 0),
        clutch_1v1_won=p.get("clutch1v1Won", 0),
        clutch_1v1_lost=p.get("clutch1v1Lost", 0),
        clutch_1v2_won=p.get("clutch1v2Won", 0),
        clutch_1v2_lost=p.get("clutch1v2Lost", 0),
        clutch_1v3_won=p.get("clutch1v3Won", 0),
        clutch_1v3_lost=p.get("clutch1v3Lost", 0),
        clutch_1v4_won=p.get("clutch1v4Won", 0),
        clutch_1v4_lost=p.get("clutch1v4Lost", 0),
        clutch_1v5_won=p.get("clutch1v5Won", 0),
        clutch_1v5_lost=p.get("clutch1v5Lost", 0),
    )


def _parse_performances(
    stats_raw: dict,
    player_lookup: dict,
    map_name_lookup: dict,
) -> list[Performance]:
    results = []

    # 全マップ合算
    for p in stats_raw["allMaps"].get("players", []):
        perf = _build_performance(p, "all", player_lookup)
        if perf:
            results.append(perf)

    # マップ別
    for m in stats_raw["maps"]:
        map_label = map_name_lookup.get(m["id"], str(m["id"]))
        for p in m.get("players", []):
            perf = _build_performance(p, map_label, player_lookup)
            if perf:
                results.append(perf)

    return results


def _parse_round_economy(
    round_economy_raw: dict,
    map_name_lookup: dict,
    team_lookup: dict,
) -> list[RoundEconomy]:
    results = []
    for map_id_str, team_data in round_economy_raw.items():
        map_id = int(map_id_str)
        map_name = map_name_lookup.get(map_id, map_id_str)
        for team_id_str, rounds in team_data.items():
            team_id = int(team_id_str)
            team_name = team_lookup.get(team_id, str(team_id))
            results.append(
                RoundEconomy(
                    map_id=map_id,
                    map_name=map_name,
                    team_id=team_id,
                    team_name=team_name,
                    rounds={str(k): int(v) for k, v in rounds.items()},
                )
            )
    return results
