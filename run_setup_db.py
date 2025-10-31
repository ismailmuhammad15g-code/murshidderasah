import asyncio
import importlib
import sys

m = importlib.import_module('main')
try:
    ok = asyncio.run(m.setup_database_once())
    print(f"setup_database_once => {ok}")
except Exception as e:
    print(f"ERROR during setup_database_once: {e}")
    sys.exit(1)
