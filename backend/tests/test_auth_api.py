import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth import AuthenticatedUser, TeamContext, require_team_member, require_user
from app.auth_repositories import AuthRepository, TeamRepository
from app.auth_schemas import TeamRead, UserRead
from app.main import app


class AuthApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user = UserRead(
            id="user-auth",
            nickname="테스터",
            name=None,
            organization=None,
            position=None,
            country=None,
            profile_completed=False,
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_signup_returns_session_and_empty_team_list(self) -> None:
        original_create_user = AuthRepository.create_user
        original_create_session = AuthRepository.create_session
        original_list = TeamRepository.list_for_user

        async def fake_create_user(_, nickname):
            self.assertEqual(nickname, "테스터")
            return self.user

        async def fake_create_session(_, user_id, token_hash):
            self.assertEqual(user_id, self.user.id)
            self.assertEqual(len(token_hash), 64)
            return datetime.now(timezone.utc) + timedelta(days=7)

        async def fake_list(_, user_id):
            self.assertEqual(user_id, self.user.id)
            return []

        AuthRepository.create_user = fake_create_user
        AuthRepository.create_session = fake_create_session
        TeamRepository.list_for_user = fake_list
        try:
            response = self.client.post("/api/v1/auth/signup", json={"nickname": "테스터"})
        finally:
            AuthRepository.create_user = original_create_user
            AuthRepository.create_session = original_create_session
            TeamRepository.list_for_user = original_list

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["token"])
        self.assertEqual(response.json()["user"]["nickname"], "테스터")
        self.assertEqual(response.json()["teams"], [])

    def test_login_rejects_unknown_nickname(self) -> None:
        original = AuthRepository.get_user_by_nickname

        async def fake_get(_, nickname):
            del nickname
            return None

        AuthRepository.get_user_by_nickname = fake_get
        try:
            response = self.client.post("/api/v1/auth/login", json={"nickname": "없는사용자"})
        finally:
            AuthRepository.get_user_by_nickname = original

        self.assertEqual(response.status_code, 404)

    def test_logout_revokes_current_session(self) -> None:
        revoked = []

        async def fake_user():
            return AuthenticatedUser(user=self.user, token_hash="hashed-token")

        original = AuthRepository.revoke_session

        async def fake_revoke(_, token_hash):
            revoked.append(token_hash)

        app.dependency_overrides[require_user] = fake_user
        AuthRepository.revoke_session = fake_revoke
        try:
            response = self.client.post("/api/v1/auth/logout")
        finally:
            AuthRepository.revoke_session = original

        self.assertEqual(response.status_code, 204)
        self.assertEqual(revoked, ["hashed-token"])

    def test_member_cannot_rename_team(self) -> None:
        complete_user = self.user.model_copy(update={"profile_completed": True})

        async def fake_member():
            return TeamContext(user=complete_user, team_id="team-auth", role="member")

        app.dependency_overrides[require_team_member] = fake_member
        response = self.client.patch(
            "/api/v1/teams/team-auth",
            headers={"X-Team-Id": "team-auth"},
            json={"name": "변경 시도"},
        )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
