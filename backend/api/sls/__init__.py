"""
SLS API路由
"""

from fastapi import APIRouter

router = APIRouter()

from . import acquisition, status, control
