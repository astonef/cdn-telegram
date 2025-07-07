import aiohttp, logging, asyncio

async def is_url_alive(url: str, retries: int = 3, delay: float = 2) -> bool:
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return True
        except Exception as e:
            logging.warning(f"try {attempt+1} failed: {e}")
        await asyncio.sleep(delay)
    return False
