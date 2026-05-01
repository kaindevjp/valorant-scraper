from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class MapResult:
    map_name: str
    team1_name: str
    team1_rounds: int
    team2_name: str
    team2_rounds: int
    winner: str


@dataclass
class PlayerStats:
    player: str
    team: str
    map: str  # "all" or map name
    rating: float
    acs: float
    kills: int
    deaths: int
    assists: int
    plus_minus: int
    kd: float
    kast: float
    adr: float
    hs_pct: float
    fbsr: float
    fb: int
    fd: int


@dataclass
class HeadToHead:
    player1: str
    player2: str
    player1_wins: int
    player2_wins: int


@dataclass
class Performance:
    player: str
    team: str
    map: str
    k2: int
    k3: int
    k4: int
    k5: int
    clutch_1v1: int
    clutch_1v2: int
    clutch_1v3: int
    clutch_1v4: int
    clutch_1v5: int
    econ: dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchData:
    match_id: str
    url: str
    team1: str
    team2: str
    date: str
    tournament: str
    maps: list[MapResult] = field(default_factory=list)
    player_stats: list[PlayerStats] = field(default_factory=list)
    head_to_head: list[HeadToHead] = field(default_factory=list)
    performances: list[Performance] = field(default_factory=list)

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
        "date": {"type": "string"},
        "tournament": {"type": "string"},
        "maps": {
            "type": "array",
            "minItems": 1,
        },
        "player_stats": {
            "type": "array",
            "minItems": 10,
        },
        "head_to_head": {"type": "array"},
        "performances": {"type": "array"},
    },
}
