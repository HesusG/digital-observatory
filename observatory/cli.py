import argparse
import asyncio
import logging
import sys

from config.settings import settings


def main():
    parser = argparse.ArgumentParser(
        prog="observatory",
        description="Digital Observatory — Intelligent opportunity monitoring",
    )
    subparsers = parser.add_subparsers(dest="command")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run the opportunity pipeline")
    pipeline_sub = pipeline_parser.add_subparsers(dest="action")

    run_parser = pipeline_sub.add_parser("run", help="Execute the pipeline")
    run_parser.add_argument("--http-only", action="store_true", help="Skip Playwright scrapers")
    run_parser.add_argument("--sources", type=str, help="Collector types: rss,wordpress,playwright")
    run_parser.add_argument("--keywords", type=str, help="Comma-separated search keywords")

    pipeline_sub.add_parser("status", help="Show last run info")

    server_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    server_parser.add_argument("--port", type=int, default=settings.app_port)

    args = parser.parse_args()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command == "pipeline" and args.action == "run":
        _run_pipeline(args)
    elif args.command == "pipeline" and args.action == "status":
        _show_status()
    elif args.command == "serve":
        _serve(args.port)
    else:
        parser.print_help()
        sys.exit(1)


def _run_pipeline(args):
    from observatory.pipeline import run_pipeline

    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None

    enable_rss = sources is None or "rss" in sources
    enable_wordpress = sources is None or "wordpress" in sources
    enable_playwright = not args.http_only and (sources is None or "playwright" in sources)

    result = asyncio.run(
        run_pipeline(
            enable_rss=enable_rss,
            enable_wordpress=enable_wordpress,
            enable_playwright=enable_playwright,
            keywords=keywords,
            source_filter=sources,
        )
    )

    print(f"\nPipeline complete:")
    print(f"  Collected:    {result.collected}")
    print(f"  Duplicates:   {result.duplicates}")
    print(f"  New items:    {result.new_items}")
    print(f"  Evaluated:    {result.evaluated}")
    print(f"  High affinity:{result.high_affinity}")
    print(f"  Notifications:{result.notifications_sent}")


def _show_status():
    from observatory.storage.state import PipelineState
    state = PipelineState(settings.state_db_path)

    last_run = state.get("last_pipeline_run")
    last_email = state.get("last_weekly_email")

    print("Pipeline Status:")
    print(f"  Last run:    {last_run or 'never'}")
    print(f"  Last email:  {last_email or 'never'}")


def _serve(port: int):
    import uvicorn
    uvicorn.run("observatory.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
