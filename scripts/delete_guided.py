#!/usr/bin/env python3
"""Delete all guided workflow executions from the database."""

import asyncio
import os

import asyncpg


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://collector:collector_dev@localhost:5432/workflow_optimizer",
)


async def main() -> None:
    conn = await asyncpg.connect(DB_URL)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(DISTINCT workflow_id) FROM event_logs"
            " WHERE activity = 'optimize:guided'"
        )
        if count == 0:
            print("No guided workflows found.")
            return

        print(f"Found {count} guided workflow(s). Deleting...")

        async with conn.transaction():
            await conn.execute(
                "DELETE FROM workflow_embeddings"
                " WHERE workflow_id IN ("
                "   SELECT DISTINCT workflow_id FROM event_logs"
                "   WHERE activity = 'optimize:guided'"
                ")"
            )
            await conn.execute(
                "DELETE FROM event_logs"
                " WHERE workflow_id IN ("
                "   SELECT DISTINCT workflow_id FROM event_logs"
                "   WHERE activity = 'optimize:guided'"
                ")"
            )

        print(f"Deleted {count} guided workflow(s) and their events.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
