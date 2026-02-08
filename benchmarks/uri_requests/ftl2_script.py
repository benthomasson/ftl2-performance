#!/usr/bin/env python3
"""HTTP requests via FTL2 uri module."""
import asyncio
import json
from ftl2 import automation


BASE_URL = "http://127.0.0.1:9199"


async def main():
    async with automation() as ftl:
        # 10x GET
        for i in range(10):
            await ftl.local.uri(
                url=f"{BASE_URL}/status",
                method="GET",
                return_content=True,
            )

        # 5x POST with JSON body
        for i in range(5):
            await ftl.local.uri(
                url=f"{BASE_URL}/data",
                method="POST",
                body=json.dumps({"name": f"benchmark-{i}", "value": i}),
                headers={"Content-Type": "application/json"},
                status_code=200,
            )


asyncio.run(main())
