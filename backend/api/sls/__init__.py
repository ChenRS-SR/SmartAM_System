"""
SLS API路由
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/sls", tags=["SLS"])

from . import acquisition, status, control
