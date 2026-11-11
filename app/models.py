"""Database and request models."""
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[str] = mapped_column(String, index=True)
    origin: Mapped[str] = mapped_column(String)
    destination: Mapped[str] = mapped_column(String)
    route_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    intermediate_hubs: Mapped[str] = mapped_column(String)
    cost_inr: Mapped[float] = mapped_column(Float)
    transit_days: Mapped[float] = mapped_column(Float)
    delay_probability: Mapped[float] = mapped_column(Float)
    congestion_risk: Mapped[float] = mapped_column(Float)
    geopolitical_risk: Mapped[float] = mapped_column(Float)


class OptimizationRequest(BaseModel):
    """Optional weights; defaults implement the assignment's 40/30/30 split."""
    cost_weight: float = Field(0.4, ge=0)
    time_weight: float = Field(0.3, ge=0)
    risk_weight: float = Field(0.3, ge=0)

    @model_validator(mode="after")
    def positive_total(self):
        if self.cost_weight + self.time_weight + self.risk_weight <= 0:
            raise ValueError("At least one optimization weight must be positive.")
        return self


class RouteInput(BaseModel):
    """Validation schema for future route-import or route-entry interfaces."""
    shipment_id: str
    origin: str
    destination: str
    route_id: str
    intermediate_hubs: str
    cost_inr: float = Field(gt=0)
    transit_days: float = Field(gt=0)
    delay_probability: float = Field(ge=0, le=1)
    congestion_risk: float = Field(ge=0, le=1)
    geopolitical_risk: float = Field(ge=0, le=1)
