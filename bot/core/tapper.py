import asyncio
import json
import random
from datetime import datetime
from urllib.parse import quote, parse_qs

import aiohttp
import pytz
from aiohttp import ClientSession
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pydantic import TypeAdapter
from pyrogram import Client, errors
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    RPCError,
    Unauthorized,
    UserAlreadyParticipant,
    UserDeactivated,
)
from pyrogram.raw.functions.account import UpdateNotifySettings
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.raw.types import InputNotifyPeer, InputPeerNotifySettings

from bot.config import settings
from bot.exceptions import InvalidSession
from bot.utils import logger

from .agents import generate_random_user_agent
from .headers import headers
from .models import QuestModel, UserData


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password,
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                    start_command_found = False

                    async for message in self.tg_client.get_chat_history(
                        "snapster_bot"
                    ):
                        if (message.text and message.text.startswith("/start")) or (
                            message.caption and message.caption.startswith("/start")
                        ):
                            start_command_found = True
                            break

                    if not start_command_found:
                        if settings.REF_ID == "":
                            await self.tg_client.send_message(
                                "snapster_bot", "/start 737844465"
                            )
                        else:
                            await self.tg_client.send_message(
                                "snapster_bot", f"/start {settings.REF_ID}"
                            )
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer("snapster_bot")
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(
                RequestWebView(
                    peer=peer,
                    bot=peer,
                    platform="android",
                    from_bot_menu=False,
                    url="https://snapster-lake.vercel.app/",
                )
            )

            tg_web_data = parse_qs(web_view.url.split("#")[1]).get("tgWebAppData")[0]
            self.user_id = (await self.tg_client.get_me()).id

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            escaped_error = str(error).replace("<", "&lt;").replace(">", "&gt;")
            logger.error(
                f"{self.session_name} | Unknown error during Authorization: {escaped_error}"
            )
            await asyncio.sleep(delay=3)

    async def get_stats(self, http_client: aiohttp.ClientSession) -> UserData:
        try:
            async with http_client.post(
                url="https://prod.snapster.bot/api/user/getUserByTelegramId",
                data=json.dumps({"telegramId": str(self.user_id)}),
            ) as response:
                res_data = await response.json()
                return UserData.model_validate(res_data["data"])
        except Exception:
            logger.exception(f"{self.session_name} | Stats error")

    async def get_quest(self, http_client: aiohttp.ClientSession) -> list[QuestModel]:
        try:
            async with http_client.get(
                url=f"https://prod.snapster.bot//api/quest/getQuests?telegramId={self.user_id}"
            ) as response:
                res_data = await response.json()
                return TypeAdapter(list[QuestModel]).validate_python(res_data["data"])
        except Exception:
            logger.exception(f"{self.session_name} | Stats error")

    async def daily_claim(self, http_client: aiohttp.ClientSession) -> bool:
        try:
            async with http_client.post(
                url="https://prod.snapster.bot/api/user/claimMiningBonus",
                json={"telegramId": f"{self.user_id}"},
            ):
                return True
        except Exception:
            logger.exception(f"{self.session_name} | Daily claim error")
            return False

    async def quest_claim(
        self, http_client: aiohttp.ClientSession, quest_id: int
    ) -> bool:
        try:
            async with http_client.post(
                url="https://prod.snapster.bot/api/quest/claimQuestBonus",
                json={"telegramId": f"{self.user_id}", "questId": quest_id},
            ) as r:
                logger.info(f"quest_claim {await r.json()}")
                return True
        except Exception:
            logger.exception(f"{self.session_name} | Quest claim error")
            return False

    async def quest_earn(
        self, http_client: aiohttp.ClientSession, quest_id: int
    ) -> bool:
        try:
            async with http_client.post(
                url="https://prod.snapster.bot/api/quest/startQuest",
                json={"telegramId": f"{self.user_id}", "questId": quest_id},
            ) as r:
                logger.info(f"quest_earn {await r.json()}")
                return True
        except Exception:
            logger.exception(f"{self.session_name} | Quest claim error")
            return False

    async def check_proxy(
        self, http_client: aiohttp.ClientSession, proxy: Proxy
    ) -> None:
        try:
            response = await http_client.get(
                url="https://httpbin.org/ip", timeout=aiohttp.ClientTimeout(5)
            )
            ip = (await response.json()).get("origin")
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            escaped_error = str(error).replace("<", "&lt;").replace(">", "&gt;")
            logger.error(
                f"{self.session_name} | Proxy: {proxy} | Error: {escaped_error}"
            )

    async def join_and_archive_channel(self, channel_name: str) -> None:
        try:
            async with self.tg_client:
                try:
                    chat = await self.tg_client.join_chat(channel_name)
                    logger.info(
                        f"{self.session_name} | Successfully joined to  <g>{chat.title}</g> successfully archived"
                    )
                except UserAlreadyParticipant:
                    logger.info(
                        f"{self.session_name} | Chat <y>{channel_name}</y> already joined"
                    )
                except RPCError as e:
                    logger.error(
                        f"{self.session_name} | Channel <y>{channel_name}</y> not found, {e}"
                    )
                    raise
                else:
                    await asyncio.sleep(random.uniform(2, 3))
                    peer = await self.tg_client.resolve_peer(chat.id)

                    await self.tg_client.invoke(
                        UpdateNotifySettings(
                            peer=InputNotifyPeer(peer=peer),
                            settings=InputPeerNotifySettings(mute_until=2147483647),
                        )
                    )
                    logger.info(
                        f"{self.session_name} | Successfully muted chat <g>{chat.title}</g> for channel <y>{channel_name}</y>"
                    )
                    await asyncio.sleep(random.uniform(2, 3))
                    await self.tg_client.archive_chats(chat_ids=[chat.id])
                    logger.info(
                        f"{self.session_name} | Channel <g>{chat.title}</g> successfully archived for channel <y>{channel_name}</y>"
                    )

        except errors.FloodWait as e:
            logger.error(
                f"{self.session_name} | Waiting {e.value} seconds before the next attempt."
            )
            await asyncio.sleep(e.value)
            raise

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)
            tg_web_data = await self.get_tg_web_data(proxy=proxy)
            while True:
                try:
                    # tg_web_data_parts = tg_web_data.split("&")
                    # query_id = tg_web_data_parts[0].split("=")[1]
                    # user_data = tg_web_data_parts[1].split("=")[1]
                    # auth_date = tg_web_data_parts[2].split("=")[1]
                    # hash_value = tg_web_data_parts[3].split("=")[1]
                    #
                    # user_data_encoded = quote(user_data)
                    # init_data = f"query_id={query_id}&user={user_data_encoded}&auth_date={auth_date}&hash={hash_value}"
                    http_client.headers["Telegram-Data"] = tg_web_data
                    http_client.headers["User-Agent"] = generate_random_user_agent(
                        device_type="android", browser_type="chrome"
                    )

                    if not tg_web_data:
                        continue

                    user_data = await self.get_stats(http_client=http_client)
                    # await self.execute_quests(http_client)
                    now_utc = datetime.now(pytz.utc)
                    await asyncio.sleep(random.uniform(2, 3))
                    if (
                        now_utc - user_data.lastMiningBonusClaimDate
                    ).total_seconds() > self.get_clime_time():
                        status = await self.daily_claim(http_client=http_client)
                        if status is True:
                            logger.success(
                                f"{self.session_name} | Daily claim successful"
                            )
                    else:
                        sleep_time = random.uniform(
                            settings.CLIME_TIME_DELTA, settings.CLIME_TIME_DELTA * 2
                        )
                        logger.info(
                            f"{self.session_name} | Can`t daily claim, going sleep {sleep_time} hour"
                        )
                        await asyncio.sleep(delay=sleep_time)
                    await asyncio.sleep(5)

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    escaped_error = str(error).replace("<", "&lt;").replace(">", "&gt;")
                    logger.error(
                        f"{self.session_name} | Unknown error: {escaped_error}"
                    )
                    await asyncio.sleep(delay=random.uniform(50, 100))

    async def execute_quests(self, http_client):
        quest = await self.get_quest(http_client)
        for q in quest:
            if q.type == "REFERRAL" or q.status == "CLAIMED":
                continue
            if q.status == "EARN":
                await self.quest_earn(http_client, q.id)
            if q.link and q.link.startswith("https://t.me/+"):
                await self.join_and_archive_channel(channel_name=q.link)
                await asyncio.sleep(random.uniform(1, 2))
                await self.quest_claim(http_client, q.id)
            try:
                await self.quest_claim(http_client, q.id)
                logger.info(
                    f"{self.session_name} | Quest <g>{q.title}</g> successfully  <y>+{q.bonusPoints}</y>"
                )
            except Exception as error:
                escaped_error = str(error).replace("<", "&lt;").replace(">", "&gt;")
                logger.error(
                    f"{self.session_name} | Quest <g>{q.title}</g> failed, {escaped_error}"
                )

    def get_clime_time(self) -> float:
        return random.uniform(settings.CLIME_TIME_DELTA, settings.CLIME_TIME_DELTA * 5)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
