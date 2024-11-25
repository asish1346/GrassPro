import asyncio
import random
import ssl
import json
import time
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# List to keep track of active proxies
active_proxies = []

async def validate_http_proxy(proxy):
    """Validate an HTTP or HTTPS proxy."""
    try:
        test_url = "https://httpbin.org/ip"
        proxies = {"http": proxy, "https": proxy}
        response = requests.get(test_url, proxies=proxies, timeout=5)
        logger.info(f"HTTP/HTTPS Proxy validated: {proxy} - Response: {response.json()}")
        return True
    except Exception as e:
        logger.warning(f"HTTP/HTTPS Proxy validation failed for {proxy}: {e}")
        return False

async def validate_socks_proxy(proxy):
    """Validate a SOCKS5 or SOCKS4 proxy."""
    try:
        test_url = "https://httpbin.org/ip"
        proxies = {"http": proxy, "https": proxy}
        response = requests.get(test_url, proxies=proxies, timeout=5)
        logger.info(f"SOCKS Proxy validated: {proxy} - Response: {response.json()}")
        return True
    except Exception as e:
        logger.warning(f"SOCKS Proxy validation failed for {proxy}: {e}")
        return False

async def validate_proxy(proxy):
    """Validate a proxy depending on its protocol."""
    if proxy.startswith("socks5://") or proxy.startswith("socks4://"):
        return await validate_socks_proxy(proxy)
    elif proxy.startswith("http://") or proxy.startswith("https://"):
        return await validate_http_proxy(proxy)
    else:
        logger.warning(f"Unsupported proxy protocol for {proxy}")
        return False

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Using proxy: {socks5_proxy}, device_id: {device_id}")
    
    # Add the proxy to active proxies list when a connection starts
    active_proxies.append(socks5_proxy)

    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            # Establish websocket connection
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:

                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(f"PING Sent: {send_message}")
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(f"Received Message: {message}")

                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "desktop",
                                "version": "4.29.0",
                            }
                        }
                        logger.debug(f"AUTH Response: {auth_response}")
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(f"PONG Response: {pong_response}")
                        await websocket.send(json.dumps(pong_response))

                    else:
                        # Unexpected message, remove proxy
                        logger.warning(f"Unexpected message: {message}. Removing proxy {socks5_proxy}")
                        remove_proxy(socks5_proxy)
                        break

        except Exception as e:
            logger.error(f"Exception with proxy {socks5_proxy}: {e}")
            remove_proxy(socks5_proxy)
            break

def remove_proxy(proxy):
    """Remove the proxy from the list of active proxies."""
    if proxy in active_proxies:
        active_proxies.remove(proxy)
        logger.info(f"Proxy {proxy} removed from active proxies.")

async def main():
    _user_id = input('Please Enter your user ID: ')
    
    # Download proxy list from a reliable source
    r = requests.get(
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text", stream=True)
    if r.status_code == 200:
        with open('auto_proxies.txt', 'wb') as f:
            for chunk in r:
                f.write(chunk)

        with open('auto_proxies.txt', 'r') as file:
            auto_proxy_list = file.read().splitlines()

    # Validate proxies and filter out bad ones
    validated_proxies = []
    for proxy in auto_proxy_list:
        valid = await validate_proxy(proxy)
        if valid:
            validated_proxies.append(proxy)

    if not validated_proxies:
        logger.error("No valid proxies found. Exiting...")
        return

    logger.info(f"Valid Proxies: {validated_proxies}")

    # Create tasks for each valid proxy
    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id)) for proxy in validated_proxies]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
