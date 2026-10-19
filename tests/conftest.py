import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402

from secure_rag.service import ChatService  # noqa: E402


@pytest.fixture(scope="session")
def service() -> ChatService:
    return ChatService()
