"""对外字段使用 camelCase；拒绝未知字段及非有限数值，避免调用方拼错参数。"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Selection(Request):
    deviceId: str = Field(min_length=1, max_length=80)
    taskId: Optional[str] = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,80}$')
    layerNo: Optional[int] = Field(default=None, ge=1)
    offset: Optional[float] = Field(default=None, ge=0)
    processingMode: Literal['archive', 'real'] = 'archive'


class Parameters(Request):
    laserPower: float = Field(default=200, ge=50, le=500)
    fillSpeed: float = Field(default=1000, ge=100, le=5000)
    layerWaitTime: float = Field(default=2, ge=0, le=600)


class Control(Selection):
    operation: Literal['preview', 'save', 'get', 'simulate', 'execute'] = 'preview'
    planId: Optional[str] = Field(default=None, max_length=80)
    requestId: Optional[str] = Field(default=None, min_length=1, max_length=80)
    regionIds: Optional[list[str]] = Field(default=None, min_length=1, max_length=4)
    currentParameters: Parameters = Field(default_factory=Parameters)
    strategy: Literal['adjust', 'remelt', 'recoat', 'stop'] = 'adjust'
    automatic: bool = True

    @model_validator(mode='after')
    def check_operation(self):
        if self.operation in ('get', 'simulate', 'execute') and not self.planId:
            raise ValueError('该操作必须提供 planId')
        if self.operation == 'save' and not self.requestId:
            raise ValueError('保存必须提供 requestId，重复请求不会产生重复方案')
        if self.regionIds and len(set(self.regionIds)) != len(self.regionIds):
            raise ValueError('regionIds 不得重复')
        return self


class Equipment(Request):
    deviceIds: Optional[list[str]] = Field(default=None, min_length=1, max_length=100)
    offset: Optional[float] = Field(default=None, ge=0)


class Maintenance(Request):
    operation: Literal['query', 'recordTask', 'recordMaintenance'] = 'query'
    deviceIds: Optional[list[str]] = Field(default=None, min_length=1, max_length=100)
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    deviceId: Optional[str] = Field(default=None, min_length=1, max_length=80)
    taskId: Optional[str] = Field(default=None, min_length=1, max_length=80)
    recordId: Optional[str] = Field(default=None, min_length=1, max_length=80)
    occurredAt: Optional[datetime] = None
    faulted: Optional[bool] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def check_record(self):
        for date in (self.startTime, self.endTime, self.occurredAt):
            if date and date.tzinfo is None:
                raise ValueError('时间须包含时区，例如 2026-11-23T09:00:00+08:00')
        if bool(self.startTime) != bool(self.endTime):
            raise ValueError('startTime 与 endTime 须同时提供')
        if self.startTime and self.startTime >= self.endTime:
            raise ValueError('startTime 须早于 endTime')
        if self.operation != 'query' and (not self.deviceId or not self.occurredAt):
            raise ValueError('登记记录必须提供 deviceId、occurredAt')
        if self.operation == 'recordTask' and (not self.taskId or self.faulted is None):
            raise ValueError('任务登记必须提供 taskId、faulted')
        if self.operation == 'recordMaintenance' and (not self.recordId or not self.description):
            raise ValueError('维护登记必须提供 recordId、description')
        return self
