from django.utils.translation import gettext_lazy as _
from bot import types


SESSION_MODES = (
    (types.SessionMode.LISTENER, _('listener')),
    (types.SessionMode.WORKER, _('worker')),
)

LOG_TYPES = (
    (types.LogType.DELETION, _('deletion')),
    (types.LogType.USERNAME_CHANGE, _('username_change')),
)

LIMITATION_TYPES = (
    (types.LimitationType.POST_VIEWS, _('limitation_type_post_views')),
    (types.LimitationType.LANGUAGE_STATS, _('limitation_type_language_stats')),
    (types.LimitationType.VIEWS_BY_SOURCE_STATS, _('limitation_type_views_by_source_stats')),
)

LIMITATION_ACTIONS = (
    (types.LimitationAction.DELETE_POST, _('limitation_action_delete_post')),
    (types.LimitationAction.CHANGE_USERNAME, _('limitation_action_change_username')),
)

STATS_VIEWS_TYPES = (
    (types.StatsViewsType.LANGUAGE, _('stats_views_type_language')),
    (types.StatsViewsType.VIEWS_BY_SOURCE, _('stats_views_type_views_by_source')),
)

USERNAME_CHANGE_REASONS = (
    (types.UsernameChangeReason.DELETIONS_LIMIT, _('deletions_limit')),
    (types.UsernameChangeReason.LANGUAGE_STATS_VIEWS_LIMIT, _('language_stats_views_limit')),
    (types.UsernameChangeReason.LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT, _('language_stats_views_difference_limit')),
    (types.UsernameChangeReason.VIEWS_BY_SOURCE_STATS_LIMIT, _('views_by_source_stats_limit')),
    (types.UsernameChangeReason.VIEWS_BY_SOURCE_STATS_DIFFERENCE_LIMIT, _('views_by_source_stats_difference_limit')),
    (types.UsernameChangeReason.THIRD_PARTY_REQUEST, _('third_party_request')),
)
