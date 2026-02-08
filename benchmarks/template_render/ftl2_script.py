#!/usr/bin/env python3
"""Render 5 config templates via FTL2."""
import asyncio
from ftl2 import automation


async def main():
    server_name = "bench-server"
    server_port = 8080

    async with automation() as ftl:
        for i in range(5):
            content = (
                f"# Server configuration {i}\n"
                f"server_name = {server_name}\n"
                f"port = {server_port + i}\n"
                f"workers = {i * 2}\n"
                f"log_level = info\n"
                f"max_connections = {i * 100}\n"
            )
            await ftl.local.copy(
                dest=f"/tmp/ftl2_bench_config_{i}.conf",
                content=content,
                mode="0644",
            )

        for i in range(5):
            await ftl.local.file(
                path=f"/tmp/ftl2_bench_config_{i}.conf",
                state="absent",
            )


asyncio.run(main())
