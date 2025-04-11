import asyncio

from telegram import run_bot
from routers import user_sessions

async def shutdown():
    print("Shutting down. Closing sessions...")
    for client in user_sessions.values():
        await client.close_session()
    print("All sessions are closed.")

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(shutdown())

