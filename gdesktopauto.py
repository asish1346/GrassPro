import asyncio
import random
import ssl
import json
import time
import uuid
import requests
import socket
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

active_proxies = []
semaphore = asyncio.Semaphore(50)  # Limit concurrent connections

async def validate_proxy(proxy):
    try:
        _, host, port = proxy.split(':')
        socket.create_connection((host, int(port.split('@')[-1])), timeout=5)
        return True
    except Exception:
        logger.warning(f"Proxy {proxy} failed validation.")
        return False

async def connect_to_wss_with_retries(socks5_proxy, user_id, retries=3):
    for attempt in range(retries):
        try:
            await connect_to_wss(socks5_proxy, user_id)
            break
        except Exception as e:
            logger.error(f"Retry {attempt + 1}/{retries} failed for proxy {socks5_proxy}: {e}")
            await asyncio.sleep(2)
    else:
        logger.error(f"All retries failed for proxy {socks5_proxy}")
        remove_proxy(socks5_proxy)

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome').random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Using proxy: {socks5_proxy}, device_id: {device_id}")
    active_proxies.append(socks5_proxy)

    urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
    uri = random.choice(urilist)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    proxy = Proxy.from_url(socks5_proxy)

    async with proxy_connect(uri, proxy=proxy, ssl=ssl_context) as websocket:
        async def send_ping():
            while True:
                try:
                    ping_message = json.dumps({"id": str(uuid.uuid4()), "action": "PING"})
                    await websocket.send(ping_message)
                    await asyncio.sleep(10)
                except Exception as e:
                    logger.error(f"Ping failed: {e}")
                    break

        asyncio.create_task(send_ping())

        while True:
            try:
                response = await websocket.recv()
                logger.info(f"Received: {response}")
            except Exception as e:
                logger.error(f"Exception in main loop: {e}")
                break

def remove_proxy(proxy):
    if proxy in active_proxies:
        active_proxies.remove(proxy)
        logger.info(f"Removed proxy: {proxy}")

async def main():
    _user_id = input("Enter user ID: ")
    r = requests.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text")
    if r.status_code == 200:
        with open("auto_proxies.txt", "wb") as f:
            f.write(r.content)
        with open("auto_proxies.txt", "r") as file:
            auto_proxy_list = file.read().splitlines()

    valid_proxies = [proxy for proxy in auto_proxy_list if await validate_proxy(proxy)]
    tasks = [connect_with_limit(proxy, _user_id) for proxy in valid_proxies]
    await asyncio.gather(*tasks)

async def connect_with_limit(proxy, user_id):
    async with semaphore:
        await connect_to_wss_with_retries(proxy, user_id)

if __name__ == "__main__":
    asyncio.run(main())
