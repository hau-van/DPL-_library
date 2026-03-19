import asyncio
import sys


def _configure_windows_asyncio() -> None:
    # psycopg async can't run on ProactorEventLoop (Windows default)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    _configure_windows_asyncio()
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="debug",
    )


if __name__ == "__main__":
    main()

