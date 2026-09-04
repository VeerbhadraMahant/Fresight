"""Test-suite bootstrap.

Set before *any* test module imports ``app``: the suite must be hermetic and
must not pick up a developer's local ``.env`` (which points at a real Supabase
DB). Tests that want a database configure one explicitly (see ``test_worker``).
"""

import os

os.environ["FREIGHTSIGHT_SKIP_DOTENV"] = "1"
os.environ.pop("DATABASE_URL", None)
