from enum import auto, StrEnum, IntEnum


class SessionMode(IntEnum):
    LISTENER = auto()
    WORKER = auto()


class LogType(StrEnum):
    DELETION = auto()
    USERNAME_CHANGE = auto()


class LimitationType(StrEnum):
    POST_VIEWS = auto()
    LANGUAGE_STATS = auto()
    VIEWS_BY_SOURCE_STATS = auto()


class LimitationAction(StrEnum):
    DELETE_POST = auto()
    CHANGE_USERNAME = auto()


class StatsViewsType(StrEnum):
    LANGUAGE = auto()
    VIEWS_BY_SOURCE = auto()


class UsernameChangeReason(StrEnum):
    DELETIONS_LIMIT = auto()
    LANGUAGE_STATS_VIEWS_LIMIT = auto()
    LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT = auto()
    VIEWS_BY_SOURCE_STATS_LIMIT = auto()
    VIEWS_BY_SOURCE_STATS_DIFFERENCE_LIMIT = auto()
    THIRD_PARTY_REQUEST = auto()
