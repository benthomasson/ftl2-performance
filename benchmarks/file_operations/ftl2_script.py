#!/usr/bin/env python3
"""Create, stat, and remove 10 temp files via FTL2."""
import asyncio
from ftl2 import automation


async def main():
    async with automation() as ftl:
        for i in range(10):
            await ftl.local.file(path=f"/tmp/ftl2_bench_{i}", state="touch")

        for i in range(10):
            await ftl.local.stat(path=f"/tmp/ftl2_bench_{i}")

        for i in range(10):
            await ftl.local.file(path=f"/tmp/ftl2_bench_{i}", state="absent")


asyncio.run(main())
