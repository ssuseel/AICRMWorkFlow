"""Analytics query filter contract."""

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class AnalyticsFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None
    owner_id: str | None = None
    industry: str | None = None
    source: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "AnalyticsFilters":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self
