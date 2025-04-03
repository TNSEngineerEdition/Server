from enum import Enum


class NodeType(Enum):
    UNKNOWN = "unknown"
    TRAM_STOP = "tram_stop"
    SWITCH = "switch"
    TRAM_CROSSING = "tram_crossing"
    CROSSING = "crossing"
    TRAM_LEVEL_CROSSING = "tram_level_crossing"
    RAILWAY_CROSSING = "railway_crossing"
    TRAM_LEVEL_AND_RAILWAY_CROSSING = "tram_level_crossing;railway_crossing"
    POWER_SUPPLY = "power_supply"
    BUFFER_STOP = "buffer_stop"
    INTERPOLATED = "interpolated"
