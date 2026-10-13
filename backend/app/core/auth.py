import logging
from typing import Optional, Dict, Any
import jwt
from fastapi import Header, HTTPException, status
from app.core.config import settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Extracts and validates Supabase JWT token from Authorization header if provided.
    Does not reject unauthenticated users in development, returning None instead.
    Returns user payload dictionary with 'id', 'email', 'role'.
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Authorization header must be formatted as 'Bearer <token>'.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        # If Supabase JWT secret is configured, verify HMAC signature
        if settings.SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_exp": True}
            )
        else:
            # Decode without secret verification if JWT secret not explicitly configured yet
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": True}
            )

        user_id = payload.get("sub") or payload.get("id")
        if not user_id:
            raise AuthenticationError("Token payload missing user subject ID.")

        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "claims": payload
        }

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired.")
    except jwt.PyJWTError as e:
        logger.warning(f"Failed to decode Supabase JWT token: {e}")
        raise AuthenticationError(f"Invalid authentication token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error validating auth token: {e}")
        raise AuthenticationError("Unable to validate user credentials.")

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Strict dependency: Requires a valid authenticated Supabase user.
    """
    user = await get_optional_current_user(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with Supabase.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
