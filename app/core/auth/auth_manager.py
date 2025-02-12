from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    STUDENT = "student"

class User(BaseModel):
    email: str
    role: UserRole
    disabled: bool = False

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class AuthManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    async def authenticate_user(self, db, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user against database"""
        user = await db.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def get_current_user(self, db, token: str = Depends(oauth2_scheme)) -> UserInDB:
        """Get current user from token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str = payload.get("sub")
            role: str = payload.get("role")
            if email is None:
                raise credentials_exception
            token_data = TokenData(email=email, role=role)
        except JWTError:
            raise credentials_exception
        user = await db.get_user_by_email(token_data.email)
        if user is None:
            raise credentials_exception
        return user

    def check_permission(self, user: UserInDB, required_role: UserRole) -> bool:
        """Check if user has required role"""
        role_hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.RESEARCHER: 2,
            UserRole.STUDENT: 1
        }
        return role_hierarchy[user.role] >= role_hierarchy[required_role]

    def require_role(self, required_role: UserRole):
        """Decorator to require specific role"""
        async def role_checker(user: UserInDB = Depends(self.get_current_user)):
            if not self.check_permission(user, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {required_role} required"
                )
            return user
        return role_checker 