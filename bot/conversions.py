from bot.types import LogType, LimitationType, LimitationAction, StatsViewsType, UsernameChangeReason


limitation_action__log_type = {
    LimitationAction.DELETE_POST: LogType.DELETION,
    LimitationAction.CHANGE_USERNAME: LogType.USERNAME_CHANGE,
}

limitation_type__stats_views = {
    LimitationType.LANGUAGE_STATS: StatsViewsType.LANGUAGE,
    LimitationType.VIEWS_BY_SOURCE_STATS: StatsViewsType.VIEWS_BY_SOURCE,
}

stats_views__username_change_reason = {
    StatsViewsType.LANGUAGE: UsernameChangeReason.LANGUAGE_STATS_VIEWS_LIMIT,
    StatsViewsType.VIEWS_BY_SOURCE: UsernameChangeReason.VIEWS_BY_SOURCE_STATS_LIMIT,
}

stats_views__username_change_reason_diff = {
    StatsViewsType.LANGUAGE: UsernameChangeReason.LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT,
    StatsViewsType.VIEWS_BY_SOURCE: UsernameChangeReason.VIEWS_BY_SOURCE_STATS_DIFFERENCE_LIMIT,
}
