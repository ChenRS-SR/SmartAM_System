"""
API 认证模块
============
提供 JWT Token 认证和 API Key 认证
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
import hashlib
import secrets

router = APIRouter()

# 安全配置
# 注意：生产环境应从环境变量读取
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


# ========== 数据模型 ==========

class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """令牌数据"""
    username: Optional[str] = None
    scopes: list = []


class User(BaseModel):
    """用户模型"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: list = []


class UserInDB(User):
    """数据库用户模型"""
    hashed_password: str


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


# ========== 密码哈希工具（替代 passlib）==========

def hash_password(password: str) -> str:
    """
    使用 SHA256 + Salt 哈希密码
    注意：生产环境建议使用 bcrypt 或 Argon2
    """
    # 生成随机 salt
    salt = secrets.token_hex(16)
    # 组合 salt 和密码进行哈希
    pwdhash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwdhash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        salt, stored_hash = hashed_password.split('$')
        pwdhash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return secrets.compare_digest(pwdhash, stored_hash)
    except Exception:
        return False


# ========== 模拟用户数据库 ==========
# 生产环境应使用真实数据库

def init_users_db():
    """初始化用户数据库（延迟初始化避免启动时计算）"""
    return {
        "admin": {
            "username": "admin",
            "full_name": "Administrator",
            "email": "admin@example.com",
            "hashed_password": hash_password("admin123"),
            "disabled": False,
            "scopes": ["admin", "write", "read"]
        },
        "operator": {
            "username": "operator",
            "full_name": "Operator",
            "email": "operator@example.com",
            "hashed_password": hash_password("operator123"),
            "disabled": False,
            "scopes": ["write", "read"]
        },
        "viewer": {
            "username": "viewer",
            "full_name": "Viewer",
            "email": "viewer@example.com",
            "hashed_password": hash_password("viewer123"),
            "disabled": False,
            "scopes": ["read"]
        }
    }


# 延迟初始化
fake_users_db = None

def get_users_db():
    """获取用户数据库（延迟初始化）"""
    global fake_users_db
    if fake_users_db is None:
        fake_users_db = init_users_db()
    return fake_users_db


# ========== 辅助函数 ==========

def get_user(db: Dict, username: str) -> Optional[UserInDB]:
    """从数据库获取用户"""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(db: Dict, username: str, password: str) -> Optional[UserInDB]:
    """验证用户"""
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ========== 依赖函数 ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    获取当前用户（JWT 认证）
    
    用法：
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"message": f"Hello {user.username}"}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    token_data = TokenData(username=username, scopes=payload.get("scopes", []))
    
    user = get_user(get_users_db(), username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        scopes=user.scopes
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


class RequireScopes:
    """
    权限范围检查依赖
    
    用法：
        @app.post("/admin-only")
        async def admin_route(user: User = Depends(RequireScopes("admin"))):
            pass
    """
    
    def __init__(self, *required_scopes: str):
        self.required_scopes = set(required_scopes)
    
    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_scopes = set(user.scopes)
        
        # 检查是否有所需权限
        if not self.required_scopes.issubset(user_scopes):
            missing = self.required_scopes - user_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，缺少: {', '.join(missing)}"
            )
        
        return user


# ========== API 端点 ==========

@router.post("/login", response_model=Token)
async def login(form_data: LoginRequest):
    """
    用户登录获取 JWT Token
    
    测试账号：
    - admin / admin123 (管理员权限)
    - operator / operator123 (操作员权限)
    - viewer / viewer123 (只读权限)
    """
    user = authenticate_user(get_users_db(), form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新访问令牌"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "scopes": current_user.scopes},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/test")
async def test_auth(current_user: User = Depends(get_current_user)):
    """测试认证是否正常工作"""
    return {
        "message": f"Hello {current_user.full_name}",
        "username": current_user.username,
        "scopes": current_user.scopes
    }


# ========== API Key 认证 ==========

class APIKeyAuth:
    """
    API Key 认证（用于服务间通信或简单场景）
    
    用法：
        @app.get("/api/protected")
        async def protected_route(api_key: str = Depends(APIKeyAuth())):
            pass
    """
    
    def __init__(self, api_key_header: str = "X-API-Key"):
        self.api_key_header = api_key_header
        # 生产环境应从环境变量或数据库读取
        self.valid_keys = {
            "dev-key-123": {"name": "Development", "scopes": ["read", "write"]},
            "monitor-key-456": {"name": "Monitoring", "scopes": ["read"]},
        }
    
    def __call__(self, api_key: Optional[str] = None) -> Dict:
        from fastapi import Request, HTTPException
        import functools
        
        # 如果直接传入 api_key 参数
        if api_key:
            if api_key not in self.valid_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的 API Key"
                )
            return self.valid_keys[api_key]
        
        # 否则返回依赖函数
        @functools.wraps(self._dependency)
        async def dependency(request: Request) -> Dict:
            key = request.headers.get(self.api_key_header)
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"缺少 {self.api_key_header} 请求头"
                )
            
            if key not in self.valid_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的 API Key"
                )
            
            return self.valid_keys[key]
        
        return dependency
    
    async def _dependency(self, request):
        pass  # 占位，实际逻辑在上面


# 创建全局 API Key 认证实例
api_key_auth = APIKeyAuth()
