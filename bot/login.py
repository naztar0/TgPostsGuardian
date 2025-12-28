import logging
import asyncio
from datetime import datetime, timezone
from telethon import TelegramClient, types, events
from telethon.sessions import StringSession
from telethon.tl.types import UpdateLoginToken
from telethon.tl.types.auth import LoginToken, LoginTokenSuccess, LoginTokenMigrateTo
from telethon.tl.functions.auth import ExportLoginTokenRequest, AcceptLoginTokenRequest, ImportLoginTokenRequest
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from django.conf import settings
from bot import models
from bot.types import SessionMode


class SkipCode(Exception): pass
def skip_code_callback(): raise SkipCode()


def update_login_token_handler(
        event: asyncio.Event,
        client: TelegramClient,
        config: models.UserBotConfig,
        session: models.UserBotSession
):
    # noinspection PyProtectedMember
    async def handle(_event: UpdateLoginToken):
        logging.info(f'Received login token')
        try:
            response = await client(ExportLoginTokenRequest(settings.API_ID, settings.API_HASH, []))
            if isinstance(response, LoginTokenMigrateTo):
                await client._switch_dc(response.dc_id)
                response = await client(ImportLoginTokenRequest(response.token))
            if isinstance(response, LoginTokenSuccess):
                logging.warning(f'Login token successfully accepted')
                await client._on_login(response.authorization.user)
                session.authorization = client.session.save()
                await session.asave()
        except SessionPasswordNeededError:
            await client.sign_in(config.phone_number, password=config.password)
            logging.warning(f'Login with password successful')
            session.authorization = client.session.save()
            await session.asave()
        finally:
            event.set()
    return handle


async def init_instances(config: models.UserBotConfig, skip_code: bool, remove_skipped: bool):
    code_callback = skip_code_callback if skip_code else None

    session = await models.UserBotSession.objects \
        .filter(userbot__phone_number=config.phone_number) \
        .order_by('id') \
        .select_related('userbot') \
        .afirst()

    if session:
        userbot = session.userbot
        listener_client = TelegramClient(StringSession(session.authorization), settings.API_ID, settings.API_HASH, receive_updates=False)
    elif not skip_code:
        userbot = None
        listener_client = TelegramClient(StringSession(), settings.API_ID, settings.API_HASH, receive_updates=False)
    else:
        if remove_skipped:
            await models.UserBot.objects.filter(phone_number=config.phone_number).adelete()
        raise SkipCode()

    try:
        # noinspection PyUnresolvedReferences
        await listener_client.start(config.phone_number, code_callback=code_callback, password=config.password)
        if not userbot:
            user: types.User = await listener_client.get_me()
            userbot = await models.UserBot.objects.acreate(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone_number=config.phone_number,
            )
        if not session:
            # noinspection PyProtectedMember
            await models.UserBotSession.objects.acreate(
                mode=SessionMode.LISTENER,
                userbot=userbot,
                authorization=listener_client.session.save()
            )
    except SkipCode:
        if remove_skipped:
            await models.UserBot.objects.filter(phone_number=config.phone_number).adelete()
        raise

    sessions: list[models.UserBotSession | None] = [
        x async for x in
        models.UserBotSession.objects.filter(userbot__phone_number=config.phone_number).order_by('id').all()
    ][1:]

    sessions.extend([None] * (config.worker_instances - len(sessions)))

    for session in sessions:
        client = TelegramClient(
            StringSession(session.authorization if session else None),
            settings.API_ID,
            settings.API_HASH,
            receive_updates=True
        )
        try:
            if session is None:
                session = await models.UserBotSession.objects.acreate(
                    mode=SessionMode.WORKER,
                    userbot=userbot
                )
                raise SkipCode()
            # noinspection PyUnresolvedReferences
            await client.start(config.phone_number, code_callback=skip_code_callback)
        except SkipCode:
            event = asyncio.Event()
            client.add_event_handler(
                update_login_token_handler(event, client, config, session),
                events.Raw(types.UpdateLoginToken)
            )
            await client.connect()
            login_token: LoginToken = await client(ExportLoginTokenRequest(settings.API_ID, settings.API_HASH, []))
            timeout = (login_token.expires - datetime.now(tz=timezone.utc)).total_seconds()
            await listener_client(AcceptLoginTokenRequest(login_token.token))
            await asyncio.wait_for(event.wait(), timeout)
        finally:
            # noinspection PyUnresolvedReferences
            await client.disconnect()
