from .expressions import (
    Expression,
    ExpressionChainError,
    ExpressionError,
    compile_chain,
    parse_chain,
    validate_chain,
)
from .factory import BuiltStrategy, FactoryError, Violation, build, build_all
from .registry import (
    TrainingView,
    available,
    build_view,
    column_choices,
    describe,
    check_route,
    entry,
    get,
    register,
    RouteMismatch,
)
from .schema import COLUMN_SOURCES, KINDS, STRATEGY_KINDS, ParamSpec, StrategyEntry
from . import examples  # noqa: F401  - registers the baselines
from . import group_by_chain  # noqa: F401  - registers the demonstration family

__all__ = [
    "COLUMN_SOURCES",
    "KINDS",
    "STRATEGY_KINDS",
    "BuiltStrategy",
    "Expression",
    "FactoryError",
    "Violation",
    "build",
    "build_all",
    "ExpressionChainError",
    "ExpressionError",
    "ParamSpec",
    "StrategyEntry",
    "TrainingView",
    "available",
    "build_view",
    "check_route",
    "RouteMismatch",
    "column_choices",
    "compile_chain",
    "describe",
    "entry",
    "get",
    "parse_chain",
    "register",
    "validate_chain",
]
