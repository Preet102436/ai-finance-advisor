"""GET /savings/suggestions - specific, actionable savings suggestions from
chatbot_prototype.py's generate_savings_suggestions_detailed(), grounded in
the current user's real transactions and budgets for the current month.

TODO (not implemented yet):
- GET  /savings/goals          list current user's savings goals
- POST /savings/goals          create a savings goal
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from chatbot_prototype import generate_savings_suggestions_detailed
from database import get_db
from deps import get_current_user
from finance_data import load_user_budgets, load_user_transactions
from models import User
from schemas import SavingsSuggestionOut

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("/suggestions", response_model=list[SavingsSuggestionOut])
def get_savings_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compares this month's actual spend per category to the user's most
    recent budget for that category, and returns a suggestion for each
    category currently over budget, naming the merchant/category driving it.
    """
    transactions = load_user_transactions(
        db, current_user.user_id, start_date=date.today().replace(day=1)
    )
    budgets = load_user_budgets(db, current_user.user_id)

    return generate_savings_suggestions_detailed(transactions, budgets)
