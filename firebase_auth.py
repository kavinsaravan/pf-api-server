import os
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, auth
import requests
import json
from typing import Optional, Dict, Any

load_dotenv('../app.env')

# Initialize Firebase Admin
credentials_string = os.getenv('FIREBASE_CREDENTIALS_JSON', '')
firebase_config_dict = json.loads(credentials_string)
cred = credentials.Certificate(firebase_config_dict)
firebase_admin.initialize_app(cred)

# You'll need your Web API Key from Firebase Console
FIREBASE_WEB_API_KEY = "AIzaSyATy8C8GXgcuVubJWAuc1ChKaT6p7dE6R0"


class FirebaseAuthAdmin:
    """Firebase Authentication using Admin SDK"""

    @staticmethod
    def sign_up(email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new user account using Firebase Admin SDK
        """
        try:
            # Create user with Firebase Admin SDK
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False  # Set to True if you want to auto-verify
            )

            # Optional: Set custom user claims (e.g., role-based access)
            # auth.set_custom_user_claims(user.uid, {'role': 'user'})

            # Generate custom token that can be used for sign-in
            custom_token = auth.create_custom_token(user.uid)

            # Optional: Generate email verification link
            verification_link = auth.generate_email_verification_link(email)

            return {
                "success": True,
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "custom_token": custom_token.decode('utf-8'),
                "verification_link": verification_link,  # Send this via email in production
                "message": "User created successfully. Use custom_token to sign in on client."
            }

        except auth.EmailAlreadyExistsError:
            return {"success": False, "error": "Email already exists"}
        except auth.InvalidPasswordError:
            return {"success": False, "error": "Invalid password (min 6 characters)"}
        except auth.InvalidEmailError:
            return {"success": False, "error": "Invalid email format"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def sign_in(email: str, password: str) -> Dict[str, Any]:
        """
        Sign in with email and password
        Note: Firebase Admin SDK doesn't provide direct password verification,
        so we still need to use REST API for password-based sign-in.
        Alternative: Use custom token approach below.
        """
        try:
            # Use Firebase REST API for password authentication
            response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
                json={
                    "email": email,
                    "password": password,
                    "returnSecureToken": True
                }
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "uid": data.get("localId"),
                    "email": data.get("email"),
                    "display_name": data.get("displayName"),
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": data.get("expiresIn")
                }
            else:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Authentication failed")
                return {"success": False, "error": error_message}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def sign_in_with_custom_token(uid: str, additional_claims: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Sign in using custom token (alternative approach using only SDK)
        This bypasses password verification - use only after verifying user credentials
        through your own system.
        """
        try:
            # Get user to verify they exist
            user = auth.get_user(uid)

            # Create custom token
            custom_token = auth.create_custom_token(uid, additional_claims)

            return {
                "success": True,
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "custom_token": custom_token.decode('utf-8'),
                "message": "Use this custom token to sign in on the client"
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def verify_id_token(id_token: str) -> Dict[str, Any]:
        """
        Verify a Firebase ID token
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {"success": True, "decoded_token": decoded_token}
        except auth.InvalidIdTokenError:
            return {"success": False, "error": "Invalid ID token"}
        except auth.ExpiredIdTokenError:
            return {"success": False, "error": "Expired ID token"}

    @staticmethod
    def create_custom_token(uid: str, additional_claims: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a custom token for a user
        """
        try:
            custom_token = auth.create_custom_token(uid, additional_claims)
            return {
                "success": True,
                "custom_token": custom_token.decode('utf-8')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_user(uid: str) -> Dict[str, Any]:
        """
        Get user by UID
        """
        try:
            user = auth.get_user(uid)
            return {
                "success": True,
                "user": {
                    "uid": user.uid,
                    "email": user.email,
                    "display_name": user.display_name,
                    "email_verified": user.email_verified,
                    "disabled": user.disabled
                }
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}

    @staticmethod
    def update_user(uid: str, **kwargs) -> Dict[str, Any]:
        """
        Update user properties
        """
        try:
            # Allowed kwargs: email, password, display_name, photo_url, disabled, email_verified
            user = auth.update_user(uid, **kwargs)
            return {
                "success": True,
                "message": "User updated successfully",
                "user": {
                    "uid": user.uid,
                    "email": user.email,
                    "display_name": user.display_name,
                    "email_verified": user.email_verified
                }
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_user(uid: str) -> Dict[str, Any]:
        """
        Delete a user account
        """
        try:
            auth.delete_user(uid)
            return {"success": True, "message": "User deleted successfully"}
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def set_custom_claims(uid: str, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set custom claims for a user (useful for role-based access)
        """
        try:
            auth.set_custom_user_claims(uid, claims)
            return {
                "success": True,
                "message": "Custom claims set successfully",
                "claims": claims
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_users(max_results: int = 100) -> Dict[str, Any]:
        """
        List all users (paginated)
        """
        try:
            users = []
            # List users, 100 at a time
            page = auth.list_users(max_results=max_results)

            for user in page.users:
                users.append({
                    "uid": user.uid,
                    "email": user.email,
                    "display_name": user.display_name,
                    "email_verified": user.email_verified
                })

            return {
                "success": True,
                "users": users,
                "has_next_page": page.has_next_page,
                "next_page_token": page.next_page_token
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def generate_password_reset_link(email: str) -> Dict[str, Any]:
        """
        Generate password reset link
        """
        try:
            link = auth.generate_password_reset_link(email)
            return {
                "success": True,
                "reset_link": link,
                "message": "Send this link to user via email"
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def revoke_refresh_tokens(uid: str) -> Dict[str, Any]:
        """
        Revoke all refresh tokens for a user (forces re-authentication)
        """
        try:
            auth.revoke_refresh_tokens(uid)
            return {
                "success": True,
                "message": "All refresh tokens revoked. User must sign in again."
            }
        except auth.UserNotFoundError:
            return {"success": False, "error": "User not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}