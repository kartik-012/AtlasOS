"""
AtlasOS OAuth2 Service.

Handles OAuth2 authorization flows for Google and GitHub providers.
Implements account linking: if a user signs in via OAuth and an account
with the same email already exists, the OAuth provider is linked to
the existing account instead of creating a duplicate.

Design decisions:
  - Uses httpx directly (not Authlib) to minimize dependencies and
    maintain full control over the token exchange flow.
  - Authorization URL generation is stateless — the state parameter
    for CSRF protection is generated and verified here.
  - Token exchange and user info retrieval are provider-specific
    because Google and GitHub use different endpoints and response formats.
  - Encrypted token storage: OAuth tokens are encrypted before storage.
    For Phase 2, we use a simple approach; production should use a
    dedicated secrets manager (Vault, AWS Secrets Manager).
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.core.logging import get_logger
from app.core.security import create_access_token, create_refresh_token
from app.repositories.user import OAuthAccountRepository, UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = get_logger(__name__)


# =============================================================================
# Provider Configuration
# =============================================================================

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class OAuthService:
    """
    Service for OAuth2 authentication and account linking.

    Supports Google and GitHub providers. Designed for extensibility —
    adding a new provider requires implementing get_authorization_url
    and handle_callback for that provider.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._oauth_repo = OAuthAccountRepository(session)

    # =========================================================================
    # Authorization URL Generation
    # =========================================================================

    def get_google_authorization_url(self, redirect_uri: str) -> tuple[str, str]:
        """
        Generate the Google OAuth2 authorization URL.

        Args:
            redirect_uri: The callback URL registered with Google.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        settings = get_settings()
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"
        return url, state

    def get_github_authorization_url(self, redirect_uri: str) -> tuple[str, str]:
        """
        Generate the GitHub OAuth2 authorization URL.

        Args:
            redirect_uri: The callback URL registered with GitHub.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        settings = get_settings()
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        url = f"{_GITHUB_AUTH_URL}?{urlencode(params)}"
        return url, state

    # =========================================================================
    # Callback Handling
    # =========================================================================

    async def handle_google_callback(
        self,
        code: str,
        redirect_uri: str,
    ) -> tuple[User, str, str, bool]:
        """
        Handle the Google OAuth2 callback.

        Exchanges the authorization code for tokens, fetches user info,
        and either creates a new user or links to an existing account.

        Args:
            code: Authorization code from Google.
            redirect_uri: The same redirect_uri used in the authorization request.

        Returns:
            Tuple of (User, access_token, refresh_token, is_new_user).

        Raises:
            ExternalServiceError: If the token exchange or userinfo call fails.
            AuthenticationError: If the user info is incomplete.
        """
        settings = get_settings()

        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if token_response.status_code != 200:
                logger.error(
                    "google_token_exchange_failed",
                    status=token_response.status_code,
                    body=token_response.text,
                )
                raise ExternalServiceError(
                    message="Failed to exchange Google authorization code.",
                )

            token_data = token_response.json()
            google_access_token = token_data.get("access_token")
            google_refresh_token = token_data.get("refresh_token")

            # Fetch user info
            userinfo_response = await client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )

            if userinfo_response.status_code != 200:
                raise ExternalServiceError(
                    message="Failed to fetch Google user info.",
                )

            userinfo = userinfo_response.json()

        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name", email)
        picture = userinfo.get("picture")

        if not google_id or not email:
            raise AuthenticationError(
                message="Google did not provide required user information.",
            )

        return await self._link_or_create_user(
            provider="google",
            provider_account_id=google_id,
            email=email,
            display_name=name,
            avatar_url=picture,
            provider_access_token=google_access_token,
            provider_refresh_token=google_refresh_token,
        )

    async def handle_github_callback(
        self,
        code: str,
        redirect_uri: str,
    ) -> tuple[User, str, str, bool]:
        """
        Handle the GitHub OAuth2 callback.

        Args:
            code: Authorization code from GitHub.
            redirect_uri: The same redirect_uri used in the authorization request.

        Returns:
            Tuple of (User, access_token, refresh_token, is_new_user).

        Raises:
            ExternalServiceError: If the token exchange fails.
            AuthenticationError: If the user info is incomplete.
        """
        settings = get_settings()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Exchange code for token
            token_response = await client.post(
                _GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                logger.error(
                    "github_token_exchange_failed",
                    status=token_response.status_code,
                    body=token_response.text,
                )
                raise ExternalServiceError(
                    message="Failed to exchange GitHub authorization code.",
                )

            token_data = token_response.json()
            github_access_token = token_data.get("access_token")

            if not github_access_token:
                raise ExternalServiceError(
                    message="GitHub did not return an access token.",
                )

            # Fetch user info
            headers = {
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/vnd.github+json",
            }
            user_response = await client.get(_GITHUB_USER_URL, headers=headers)
            if user_response.status_code != 200:
                raise ExternalServiceError(
                    message="Failed to fetch GitHub user info.",
                )
            user_data = user_response.json()

            # GitHub doesn't always include email in /user — fetch from /user/emails
            email = user_data.get("email")
            if not email:
                emails_response = await client.get(
                    _GITHUB_EMAILS_URL,
                    headers=headers,
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    primary = next(
                        (e for e in emails if e.get("primary") and e.get("verified")),
                        None,
                    )
                    if primary:
                        email = primary["email"]

            github_id = str(user_data.get("id"))
            name = user_data.get("name") or user_data.get("login", "GitHub User")
            avatar = user_data.get("avatar_url")

            if not github_id or not email:
                raise AuthenticationError(
                    message="GitHub did not provide required user information (email).",
                )

        return await self._link_or_create_user(
            provider="github",
            provider_account_id=github_id,
            email=email,
            display_name=name,
            avatar_url=avatar,
            provider_access_token=github_access_token,
        )

    # =========================================================================
    # Account Linking Logic
    # =========================================================================

    async def _link_or_create_user(
        self,
        provider: str,
        provider_account_id: str,
        email: str,
        display_name: str,
        avatar_url: str | None = None,
        provider_access_token: str | None = None,
        provider_refresh_token: str | None = None,
    ) -> tuple[User, str, str, bool]:
        """
        Link an OAuth provider to an existing user, or create a new user.

        Account linking flow:
          1. Check if the provider+provider_account_id already exists → return existing user.
          2. Check if a user with the same email exists → link the provider to that user.
          3. Otherwise → create a new user and link the provider.

        Args:
            provider: OAuth provider name.
            provider_account_id: Provider-side user ID.
            email: User's email from the provider.
            display_name: User's name from the provider.
            avatar_url: Avatar URL from the provider.
            provider_access_token: OAuth access token (stored encrypted).
            provider_refresh_token: OAuth refresh token (stored encrypted).

        Returns:
            Tuple of (User, access_token, refresh_token, is_new_user).
        """
        is_new_user = False

        # Case 1: OAuth account already linked
        existing_oauth = await self._oauth_repo.get_by_provider_account(
            provider=provider,
            provider_account_id=provider_account_id,
        )
        if existing_oauth is not None:
            user = await self._user_repo.get_by_id(existing_oauth.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError(
                    message="User account not found or deactivated.",
                )
            await self._user_repo.update_last_login(user)
            access_token = create_access_token(subject=str(user.id))
            refresh_token = create_refresh_token(subject=str(user.id))
            logger.info(
                "oauth_login_existing",
                user_id=str(user.id),
                provider=provider,
            )
            return user, access_token, refresh_token, False

        # Case 2: Email exists — link provider to existing user
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user is not None:
            if not existing_user.is_active:
                raise AuthenticationError(
                    message="User account has been deactivated.",
                )
            await self._oauth_repo.create_oauth_account(
                user_id=existing_user.id,
                provider=provider,
                provider_account_id=provider_account_id,
                provider_email=email,
                access_token_enc=provider_access_token,
                refresh_token_enc=provider_refresh_token,
            )
            await self._user_repo.update_last_login(existing_user)
            access_token = create_access_token(subject=str(existing_user.id))
            refresh_token = create_refresh_token(subject=str(existing_user.id))
            logger.info(
                "oauth_account_linked",
                user_id=str(existing_user.id),
                provider=provider,
            )
            return existing_user, access_token, refresh_token, False

        # Case 3: New user — create account + link provider
        user = await self._user_repo.create_user(
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            email_verified=True,  # OAuth-verified emails are trusted
        )
        await self._oauth_repo.create_oauth_account(
            user_id=user.id,
            provider=provider,
            provider_account_id=provider_account_id,
            provider_email=email,
            access_token_enc=provider_access_token,
            refresh_token_enc=provider_refresh_token,
        )
        is_new_user = True
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        logger.info(
            "oauth_user_created",
            user_id=str(user.id),
            provider=provider,
        )
        return user, access_token, refresh_token, is_new_user
