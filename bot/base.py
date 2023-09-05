import logging
import time
import typing
from pyrogram import Client, errors
from pyrogram.connection.connection import Connection
from pyrogram.raw import functions, types
from bot.utils_lib import rsa

_DISCONNECT_EXPORTED_AFTER = 60
LAYER = 160


class _ExportState:
    def __init__(self):
        self._n = 0
        self._zero_ts = 0
        self._connected = False

    def add_borrow(self):
        self._n += 1
        self._connected = True

    def add_return(self):
        self._n -= 1
        assert self._n >= 0, 'returned sender more than it was borrowed'
        if self._n == 0:
            self._zero_ts = time.time()

    def should_disconnect(self):
        return (self._n == 0
                and self._connected
                and (time.time() - self._zero_ts) > _DISCONNECT_EXPORTED_AFTER)

    def need_connect(self):
        return not self._connected

    def mark_disconnected(self):
        assert self.should_disconnect(), 'marked as disconnected when it was borrowed'
        self._connected = False


# noinspection PyTypeChecker
class BaseApp:
    def __init__(self):
        self.client: Client = None
        self._borrowed_senders: dict[int, tuple] = {}
        self._cdn_config = None
        self._config = None
        self._server_keys = {}

    def _get_dc(self, dc_id, cdn=False):
        if not self._config:
            self._config = self.client.invoke(functions.help.GetConfig())

        if cdn and not self._cdn_config:
            self._cdn_config: types.CdnConfig = self.client.invoke(functions.help.GetCdnConfig())
            for pk in self._cdn_config.public_keys:
                rsa.add_key(pk.public_key, self._server_keys, old=False)

        try:
            return next(
                dc for dc in self._config.dc_options
                if dc.id == dc_id
                and bool(dc.ipv6) == self.client.ipv6 and bool(dc.cdn) == cdn
            )
        except StopIteration:
            logging.warning(f'Failed to get DC {dc_id} (cdn = {cdn}) with use_ipv6 = {self.client.ipv6}; retrying ignoring IPv6 check')
            return next(
                dc for dc in self._config.dc_options
                if dc.id == dc_id and bool(dc.cdn) == cdn
            )

    def _create_exported_sender(self, dc_id):
        dc = self._get_dc(dc_id)
        logging.info(f'Exporting auth for new borrowed sender in {dc}')

        auth: types.auth.ExportedAuthorization = self.client.invoke(functions.auth.ExportAuthorization(dc_id=dc_id))
        query = functions.auth.ImportAuthorization(id=auth.id, bytes=auth.bytes)
        req = functions.InvokeWithLayer(layer=LAYER, query=query)

        connection = Connection(dc.ip_address, dc.port, dc.id, self.client.ipv6, self.client.proxy)
        connection.connect()
        connection.send(req)
        return connection

    def _borrow_exported_sender(self, dc_id):
        logging.debug(f'Borrowing sender for dc_id {dc_id}')
        state, connection = self._borrowed_senders.get(dc_id, (None, None))

        if state is None:
            state = _ExportState()
            connection: Connection = self._create_exported_sender(dc_id)
            connection.dc_id = dc_id
            self._borrowed_senders[dc_id] = (state, connection)

        elif state.need_connect():
            connection.connect()

        state.add_borrow()
        return connection

    def _return_exported_sender(self, sender):
        logging.debug(f'Returning borrowed sender for dc_id {sender.dc_id}')
        state, _ = self._borrowed_senders[sender.dc_id]
        state.add_return()

    def get_stats_with_graphs(self, peer_id: int, graph_request_types: typing.Sequence[str]):
        def get_graphs(request, connection: Connection):
            result: types.stats.BroadcastStats = connection.send(request)
            graphs = []
            for req_type in graph_request_types:
                token = getattr(result, req_type).token
                request = functions.stats.LoadAsyncGraph(token=token)
                graph: types.StatsGraph = connection.send(request)
                graphs.append(graph)
            return result, graphs

        peer = self.client.resolve_peer(peer_id=peer_id)
        req = None
        try:
            req = functions.stats.GetBroadcastStats(channel=peer)
            return get_graphs(req, self.client.session.connection)
        except errors.StatsMigrate as e:
            dc = e.value
        except errors.BroadcastRequired:
            req = functions.stats.GetMegagroupStats(channel=peer)
            try:
                return get_graphs(req, self.client.session.connection)
            except errors.StatsMigrate as e:
                dc = e.value

        conn = self._borrow_exported_sender(dc)
        try:
            return get_graphs(req, conn)
        finally:
            self._return_exported_sender(conn)
