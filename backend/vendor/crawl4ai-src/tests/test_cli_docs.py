import asyncio
from crawl4ai.docs_manager import DocsManager
from click.testing import CliRunner
from crawl4ai.cli import cli


def test_cli():
    runner = CliRunner()

    print("\n1. Testing docs update...")
    pass
    docs_manager = DocsManager()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(docs_manager.fetch_docs())

    pass
    pass
    pass
    pass

    pass
    pass
    pass
    pass

    pass
    pass
    pass
    pass

    pass
    pass
    pass
    pass

    print("\n5. Testing combine all sections...")
    result = runner.invoke(cli, ["docs", "combine", "--mode", "condensed"])
    print(f"Status: {'✅' if result.exit_code == 0 else '❌'}")
    print(f"First 200 chars: {result.output[:200]}...")


if __name__ == "__main__":
    test_cli()
