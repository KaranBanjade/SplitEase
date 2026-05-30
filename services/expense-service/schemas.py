from uuid import UUID
from datetime import datetime
from datetime import date as Date
from decimal import Decimal
from pydantic import BaseModel, field_validator

from models import SplitType, MemberRole, RecurringFrequency


# ---------------------------------------------------------------------------
# User (embedded from auth service)
# ---------------------------------------------------------------------------

class UserInfo(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None = None


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    currency: str = "USD"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Group name cannot be blank")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    currency: str | None = None

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class GroupMemberResponse(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    role: MemberRole
    joined_at: datetime
    user: UserInfo | None = None

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    currency: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    members: list[GroupMemberResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Expense splits
# ---------------------------------------------------------------------------

class ExpenseSplitInput(BaseModel):
    """Input for a single participant in an expense split."""
    user_id: UUID
    amount: Decimal | None = None       # used for exact splits
    percentage: Decimal | None = None   # used for percentage splits


class ExpenseSplitResponse(BaseModel):
    id: UUID
    expense_id: UUID
    user_id: UUID
    share_amount: Decimal
    owed_amount: Decimal
    settled_at: datetime | None
    user: UserInfo | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

class ExpenseCreate(BaseModel):
    group_id: UUID
    description: str
    amount: Decimal
    currency: str = "USD"
    paid_by: UUID
    category: str = "general"
    date: Date
    split_type: SplitType = SplitType.equal
    splits: list[ExpenseSplitInput] = []
    is_recurring: bool = False
    recurring_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class ExpenseUpdate(BaseModel):
    description: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    paid_by: UUID | None = None
    category: str | None = None
    date: Date | None = None
    split_type: SplitType | None = None
    splits: list[ExpenseSplitInput] | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v


class ExpenseResponse(BaseModel):
    id: UUID
    group_id: UUID
    description: str
    amount: Decimal
    currency: str
    paid_by: UUID
    category: str
    date: Date
    split_type: SplitType
    is_recurring: bool
    recurring_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    splits: list[ExpenseSplitResponse] = []
    paid_by_user: UserInfo | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

class SettlementCreate(BaseModel):
    group_id: UUID
    paid_by: UUID
    paid_to: UUID
    amount: Decimal
    currency: str = "USD"
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class SettlementResponse(BaseModel):
    id: UUID
    group_id: UUID
    paid_by: UUID
    paid_to: UUID
    amount: Decimal
    currency: str
    notes: str | None
    created_at: datetime
    paid_by_user: UserInfo | None = None
    paid_to_user: UserInfo | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Recurring expense
# ---------------------------------------------------------------------------

class RecurringExpenseCreate(BaseModel):
    group_id: UUID
    description: str
    amount: Decimal
    currency: str = "USD"
    paid_by: UUID
    split_type: SplitType = SplitType.equal
    frequency: RecurringFrequency
    next_due: Date

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class RecurringExpenseUpdate(BaseModel):
    description: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    paid_by: UUID | None = None
    split_type: SplitType | None = None
    frequency: RecurringFrequency | None = None
    next_due: Date | None = None
    is_active: bool | None = None


class RecurringExpenseResponse(BaseModel):
    id: UUID
    group_id: UUID
    description: str
    amount: Decimal
    currency: str
    paid_by: UUID
    split_type: SplitType
    frequency: RecurringFrequency
    next_due: Date
    is_active: bool
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Paginated wrapper (generic via subclass)
# ---------------------------------------------------------------------------

class PaginatedExpenseResponse(BaseModel):
    items: list[ExpenseResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Balance / Debt
# ---------------------------------------------------------------------------

class BalanceResponse(BaseModel):
    user_id: UUID
    amount: Decimal
    user: UserInfo | None = None


class SimplifiedDebtResponse(BaseModel):
    from_user_id: UUID
    to_user_id: UUID
    amount: Decimal
    currency: str
    from_user: UserInfo | None = None
    to_user: UserInfo | None = None
