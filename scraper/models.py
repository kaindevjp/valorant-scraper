from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MapResult:
    map_id: int
    map_name: str
    team1_id: int
    team1_name: str
    team1_rounds: int
    team2_id: int
    team2_name: str
    team2_rounds: int
    winner: str  # チーム名


@dataclass
class PlayerStats:
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    map: str          # "all" またはマップ名
    rating: float
    acs: float
    kills: int
    deaths: int
    assists: int
    plus_minus: int   # kills - deaths
    kd: float
    kast: float
    adr: float
    hs_pct: float
    fbsr: float       # firstBloodSuccessRate (%)
    fb: int           # firstBloods
    fd: int           # firstDeaths
    econ_rating: float
    total_spent: int


@dataclass
class HeadToHead:
    """attacker が victim を kills 回キルした（マップ単位）"""
    map_id: int       # 0 = 全マップ合算
    map_name: str     # "all" or マップ名
    attacker_id: int
    attacker_name: str
    victim_id: int
    victim_name: str
    kills: int


@dataclass
class Performance:
    player_id: int
    player_name: str
    team_name: str
    map: str          # "all" またはマップ名
    k2: int
    k3: int
    k4: int
    k5: int
    clutch_1v1_won: int
    clutch_1v1_lost: int
    clutch_1v2_won: int
    clutch_1v2_lost: int
    clutch_1v3_won: int
    clutch_1v3_lost: int
    clutch_1v4_won: int
    clutch_1v4_lost: int
    clutch_1v5_won: int
    clutch_1v5_lost: int


@dataclass
class RoundEconomy:
    """チーム単位・ラウンド別の使用金額"""
    map_id: int
    map_name: str
    team_id: int
    team_name: str
    rounds: dict[str, int] = field(default_factory=dict)  # {round_no: amount}


@dataclass
class MatchData:
    match_id: str
    url: str
    team1_id: int
    team1: str
    team1_score: int  # シリーズスコア
    team2_id: int
    team2: str
    team2_score: int
    date: str
    tournament: str
    maps: list[MapResult] = field(default_factory=list)
    player_stats: list[PlayerStats] = field(default_factory=list)
    head_to_head: list[HeadToHead] = field(default_factory=list)
    performances: list[Performance] = field(default_factory=list)
    round_economy: list[RoundEconomy] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


MATCH_SCHEMA = {
    "type": "object",
    "required": ["match_id", "url", "team1", "team2", "maps", "player_stats"],
    "properties": {
        "match_id": {"type": "string"},
        "url": {"type": "string"},
        "team1": {"type": "string"},
        "team2": {"type": "string"},
        "maps": {"type": "array", "minItems": 1},
        "player_stats": {"type": "array", "minItems": 10},
        "head_to_head": {"type": "array"},
        "performances": {"type": "array"},
        "round_economy": {"type": "array"},
    },
}
