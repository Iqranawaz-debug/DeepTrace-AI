"""Bounded manual workspace contracts."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1000)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvestigationCreate(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    title: Title
    question: Question
    description: Description | None = None


class InvestigationEdit(StrictModel):
    title: Title
    question: Question
    description: Description | None = None
    expected_updated_at: str = Field(min_length=1, max_length=50)


class Investigation(StrictModel):
    id: UUID
    title: str
    question: str
    description: str | None
    status: Literal["draft"]
    created_at: str
    updated_at: str


class InvestigationList(StrictModel):
    items: list[Investigation]
    total: int


class PlanItem(StrictModel):
    id: UUID
    sub_question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    search_query: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None


class PlanSave(StrictModel):
    expected_revision: int = Field(ge=0, strict=True)
    items: list[PlanItem] = Field(max_length=8)

    @model_validator(mode="after")
    def unique_ids(self) -> PlanSave:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Step identifiers must be unique")
        return self


class Plan(StrictModel):
    id: UUID | None
    revision_no: int
    items: list[PlanItem]
