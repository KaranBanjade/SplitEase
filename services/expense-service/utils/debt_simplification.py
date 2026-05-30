from decimal import Decimal
from uuid import UUID


def simplify_debts(balances: dict[UUID, Decimal]) -> list[tuple[UUID, UUID, Decimal]]:
    """
    Given a dict of {user_id: net_balance} where positive = owed money,
    negative = owes money, returns the minimum list of
    (debtor, creditor, amount) tuples.

    Algorithm: greedy matching of the largest creditor with the largest debtor.
    """
    EPSILON = Decimal("0.01")

    creditors: list[list] = []  # [amount, user_id] – positive balances
    debtors: list[list] = []    # [amount, user_id] – absolute value of negative balances

    for user_id, balance in balances.items():
        if balance > EPSILON:
            creditors.append([balance, user_id])
        elif balance < -EPSILON:
            debtors.append([-balance, user_id])

    # Sort descending so we always match the largest amounts first
    creditors.sort(reverse=True)
    debtors.sort(reverse=True)

    transactions: list[tuple[UUID, UUID, Decimal]] = []

    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        credit_amount, creditor = creditors[i]
        debt_amount, debtor = debtors[j]

        settle = min(credit_amount, debt_amount)
        transactions.append((debtor, creditor, settle.quantize(Decimal("0.01"))))

        creditors[i][0] -= settle
        debtors[j][0] -= settle

        if creditors[i][0] < EPSILON:
            i += 1
        if debtors[j][0] < EPSILON:
            j += 1

    return transactions


def calculate_group_balances(
    expenses: list,     # list of (paid_by, [(user_id, owed_amount), ...])
    settlements: list,  # list of (paid_by, paid_to, amount)
) -> dict[UUID, Decimal]:
    """
    Calculate net balance for each user in a group.

    Positive balance  → user is owed money by the group.
    Negative balance  → user owes money to the group.
    """
    balances: dict[UUID, Decimal] = {}

    def add(user_id: UUID, amount: Decimal) -> None:
        balances[user_id] = balances.get(user_id, Decimal(0)) + amount

    for paid_by, splits in expenses:
        for user_id, owed_amount in splits:
            if user_id != paid_by:
                add(paid_by, owed_amount)    # payer is owed this amount
                add(user_id, -owed_amount)   # this person owes the payer

    for paid_by, paid_to, amount in settlements:
        # paid_by repaid some debt → their negative balance improves
        add(paid_by, amount)
        # paid_to received the money → their positive balance decreases
        add(paid_to, -amount)

    return balances
