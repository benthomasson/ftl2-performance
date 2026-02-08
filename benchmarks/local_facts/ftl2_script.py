#!/usr/bin/env python3
"""Gather local facts via FTL2."""
import asyncio
from ftl2 import automation


async def main():
    async with automation() as ftl:
        await ftl.local.setup()


asyncio.run(main())
