class PlanConflictError(Exception):
    """The requested plan mutation conflicts with the active-plan invariant."""


class PlanIntegrityError(Exception):
    """Stored or generated plan data failed the plan boundary validation."""
