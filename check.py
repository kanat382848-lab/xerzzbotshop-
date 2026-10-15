import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    headers = {"X-API-Key": os.getenv("BALA_API_KEY")}
    async with aiohttp.ClientSession() as s:
        async with s.get("https://158.247.231.14/api/v1/catalog", headers=headers) as r:
            data = await r.json()
            products = data.get("products") or data.get("items") or []
            print(f"Барлығы: {len(products)} тауар\n")
            for p in products:
                print(f"ID: {p.get('id')} | {p.get('name')} | {p.get('price_pcoins')} PC")

asyncio.run(main())