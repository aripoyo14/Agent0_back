from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class NetworkRouteRequest(BaseModel):
    user_id: str = Field(..., description="起点となる省内ユーザーID (U)")
    expert_id: str = Field(..., description="対象の外部有識者ID (Z)")
    window_days: int = Field(180, ge=1, le=3650)
    half_life_days: int = Field(90, ge=1, le=3650)
    overlap_config_id: int = Field(1, ge=1)
    overlap_coef: float = Field(0.4, ge=0.0, le=10.0)
    max_results: int = Field(5, ge=1, le=50)


class RouteHop(BaseModel):
    id: str
    type: Literal["user", "expert"]
    name: Optional[str] = None


class RouteBreakdown(BaseModel):
    ux_score: Optional[float] = None
    um_score: Optional[float] = None
    mx_score: Optional[float] = None
    xz_score: float


class NetworkRoute(BaseModel):
    path: List[RouteHop]
    score: float
    breakdown: RouteBreakdown


class NetworkRouteResponse(BaseModel):
    routes: List[NetworkRoute]


