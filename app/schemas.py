from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

# --- USER ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    model_config = {"from_attributes": True}


# --- LOGIN JSON ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- BOARD ---
class BoardBase(BaseModel):
    title: str

class BoardCreate(BoardBase):
    pass

class BoardGet(BoardBase):
    id: int
    owner_id: int
    model_config = {"from_attributes": True}


# --- TOKEN ---
class Token(BaseModel):
    access_token: str
    token_type: str


# --- LABELS ---
class LabelBase(BaseModel):
    name: str = Field(..., max_length=30)
    color: str = Field(..., max_length=20)

class LabelCreate(LabelBase):
    pass

class Label(LabelBase):
    id: int
    card_id: int
    model_config = {"from_attributes": True}


class LabelTemplateBase(BaseModel):
    name: str
    color: str

class LabelTemplate(LabelTemplateBase):
    id: int
    model_config = {"from_attributes": True}


# --- SUBTASKS ---
class SubtaskBase(BaseModel):
    title: str = Field(..., max_length=100)
    completed: bool = False

class SubtaskCreate(SubtaskBase):
    pass

class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    completed: Optional[bool] = None

class Subtask(SubtaskBase):
    id: int
    card_id: int
    model_config = {"from_attributes": True}


# --- CARD ---
class CardBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    description: Optional[str] = None
    due_date: Optional[date] = None

class CardCreate(CardBase):
    list_id: int
    board_id: int

class CardMove(BaseModel):
    list_id: int
    order: int

class CardUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = None
    due_date: Optional[date] = None
    list_id: Optional[int] = None

class Card(CardBase):
    id: int
    list_id: int
    order: int
    board_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    labels: List[Label] = []
    subtasks: List[Subtask] = []
    model_config = {"from_attributes": True}


# --- LIST ---
class CardInList(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    order: int
    due_date: Optional[date] = None
    model_config = {"from_attributes": True}

class ListSchema(BaseModel):
    id: int
    title: str
    position: int
    board_id: int
    cards: List[CardInList] = []
    model_config = {"from_attributes": True}


# --- WORKLOG ---
class WorklogBase(BaseModel):
    date: date
    hours: float = Field(..., gt=0)
    note: Optional[str] = Field(None, max_length=200)

class WorklogCreate(WorklogBase):
    card_id: int

class WorklogUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    date: Optional[str] = None
    hours: Optional[float] = None
    note: Optional[str] = None

class Worklog(BaseModel):
    id: int
    card_id: int
    user_id: int
    date: date
    hours: float
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}

class WorklogResponse(BaseModel):
    id: int
    card_id: int
    card_title: str
    date: date
    hours: float
    note: Optional[str]
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = {"from_attributes": True}


# --- REBUILD MODELS ---
Label.model_rebuild()
LabelTemplate.model_rebuild()
Subtask.model_rebuild()
Card.model_rebuild()
CardInList.model_rebuild()
ListSchema.model_rebuild()
Worklog.model_rebuild()
WorklogResponse.model_rebuild()

