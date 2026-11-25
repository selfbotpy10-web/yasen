import asyncio
import os
import sys

async def run_service(name, command):
    while True:
        print(f"Starting {name}...", flush=True)

        process = await asyncio.create_subprocess_exec(
            *command,
            env=os.environ.copy()
        )

        code = await process.wait()
        print(f"{name} stopped with code {code}", flush=True)
        print(f"Restarting {name} in 3 seconds...", flush=True)

        await asyncio.sleep(3)

async def main():
    port = os.environ.get("PORT", "8080")

    bot_command = [
        sys.executable, "-u", "bot.py"
    ]

    web_command = [
        sys.executable, "-m", "uvicorn",
        "webapp:app",
        "--host", "0.0.0.0",
        "--port", port
    ]

    await asyncio.gather(
        run_service("Telegram Bot", bot_command),
        run_service("NIRO Mini App", web_command)
    )

if __name__ == "__main__":
    asyncio.run(main())
