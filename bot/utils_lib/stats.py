import typing
from telethon import TelegramClient, types, hints, helpers, functions, errors
from telethon.tl.functions.stats import LoadAsyncGraphRequest


async def _get_graphs(request, sndr, graph_request_types):
    result: types.stats.BroadcastStats = await sndr(request)
    graphs = []
    for req_type in graph_request_types:
        token = getattr(result, req_type).token
        request = LoadAsyncGraphRequest(token)
        graph: types.StatsGraph = await sndr(request)
        graphs.append(graph)
    return result, graphs


# noinspection PyProtectedMember,PyTypeChecker
async def get_stats_with_graphs(
        client: 'TelegramClient',
        entity: 'hints.EntityLike',
        graph_request_types: typing.Sequence[str],
):
    entity = await client.get_input_entity(entity)
    if helpers._entity_type(entity) != helpers._EntityType.CHANNEL:
        raise TypeError('You must pass a channel entity')

    req = None
    try:
        req = functions.stats.GetBroadcastStatsRequest(entity)
        return await _get_graphs(req, client, graph_request_types)
    except errors.StatsMigrateError as e:
        dc = e.dc
    except errors.BroadcastRequiredError:
        req = functions.stats.GetMegagroupStatsRequest(entity)
        try:
            return await _get_graphs(req, client, graph_request_types)
        except errors.StatsMigrateError as e:
            dc = e.dc

    sender = await client._borrow_exported_sender(dc)
    try:
        return await _get_graphs(req, sender.send, graph_request_types)
    finally:
        await client._return_exported_sender(sender)
