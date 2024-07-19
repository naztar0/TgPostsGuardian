from bot.utils_lib import helper


class Log(helper.HelperMode):
    mode = helper.HelperMode.SCREAMING_SNAKE_CASE
    DELETION = helper.Item()
    USERNAME_CHANGE = helper.Item()


class UsernameChangeReason(helper.HelperMode):
    mode = helper.HelperMode.SCREAMING_SNAKE_CASE
    DELETIONS_LIMIT = helper.Item()
    LANGUAGE_STATS_VIEWS_LIMIT = helper.Item()
    LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT = helper.Item()
    THIRD_PARTY_REQUEST = helper.Item()
