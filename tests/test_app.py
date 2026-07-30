import sys
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from jwt.exceptions import DecodeError


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

    async def test_invalid_jwt_is_rejected_with_401(self):
        handler = AsyncMock()

        with patch(
            "app.jwt_authorization_middleware",
            new_callable=AsyncMock,
            side_effect=DecodeError("Not enough segments"),
        ) as jwt:
            response = await authorization_middleware(
                SimpleNamespace(path="/api/messages"), handler
            )

        self.assertEqual(401, response.status)
        self.assertEqual(
            {"error": "Invalid authorization token."}, json.loads(response.text)
        )
        jwt.assert_awaited_once()
        handler.assert_not_awaited()

    async def test_jwt_without_key_id_is_rejected_with_401(self):
        handler = AsyncMock()

        with patch(
            "app.jwt_authorization_middleware",
            new_callable=AsyncMock,
            side_effect=KeyError("kid"),
        ):
            response = await authorization_middleware(
                SimpleNamespace(path="/api/messages"), handler
            )

        self.assertEqual(401, response.status)
        handler.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
