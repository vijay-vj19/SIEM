from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


class SeverityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserTypeEnum(str, Enum):
    service_account = "service_account"
    standard_user = "standard_user"
    admin_user = "admin_user"


class TicketIn(BaseModel):
    ticket_id: str
    severity: SeverityEnum
    status: str = "OPEN"
    created_time: str
    rule_triggered: str
    mitre_attack: str
    user: str
    user_type: UserTypeEnum
    source_asset: str
    source_ip: str
    target_asset: str
    target_ip: str
    process: str
    command_line: str
    decoded_command: str
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: str
    historical_tp_count: int = Field(ge=0)
    historical_fp_count: int = Field(ge=0)


REQUIRED_EXCEL_COLUMNS = [
    "ticket_id",
    "severity",
    "status",
    "created_time",
    "rule_triggered",
    "mitre_attack",
    "user",
    "user_type",
    "source_asset",
    "source_ip",
    "target_asset",
    "target_ip",
    "process",
    "command_line",
    "decoded_command",
    "hour_of_day",
    "day_of_week",
    "historical_tp_count",
    "historical_fp_count",
]
