import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app import authorization_middleware


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_routes_bypass_jwt_authorization(self):
        handler = AsyncMock(return_value="healthy")

        with patch("app.jwt_authorization_middleware", new_callable=AsyncMock) as jwt:
            response = await authorization_middleware(
                SimpleNamespace(path="/healthz"), handler
            )

        self.assertEqual("healthy", response)
        handler.assert_awaited_once()
        jwt.assert_not_awaited()

    async def test_message_route_uses_jwt_authorization(self):
        handler = AsyncMock(return_value="protected")

        with patch(
            "app.jwt_authorization_middleware",
            new_callable=AsyncMock,
            return_value="protected",
        ) as jwt:
            response = await authorization_middleware(
                SimpleNamespace(path="/api/messages"), handler
            )

        self.assertEqual("protected", response)
        jwt.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
