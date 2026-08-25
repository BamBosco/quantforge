"""Configuration validation for the safe default runtime profile."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True, slots=True)
class RiskSettings:
    """Risk values required before any risk component can be constructed."""

    risk_per_trade: float
    max_daily_drawdown: float
    max_total_drawdown: float
    max_correlated_open_risk: float
    require_stop_loss: bool


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Execution safety controls for a runtime profile."""

    environment: str
    trading_mode: str
    live_trading_enabled: bool


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated platform settings, excluding secrets."""

    runtime: RuntimeSettings
    risk: RiskSettings


class ForexMT5DemoConfigurationError(ValueError):
    """Raised when the USD/JPY MT5 demo profile violates its safety contract."""


@dataclass(frozen=True, slots=True)
class XAUUSDReadOnlyBrokerProfile:
    """Observed XAUUSD broker facts, deliberately excluding strategy and risk policy."""

    internal_symbol: str
    broker_symbol: str
    timeframe: str
    account_currency: str
    demo_only: bool
    order_submission_enabled: bool
    audit_journal_path: str
    unresolved_requirements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ForexInstrumentSettings:
    """Stable internal identity and configurable broker mapping for one FX pair."""

    internal_symbol: str
    broker_symbol: str
    timeframe: str
    closed_candles_only: bool


@dataclass(frozen=True, slots=True)
class DemoExecutionSettings:
    """Phase-1 execution boundary: configuration may never authorize an order."""

    account_mode: str
    live_trading_enabled: bool
    order_submission_enabled: bool
    magic_number: int
    deviation_points: int
    filling_mode: str


@dataclass(frozen=True, slots=True)
class ForexRiskSettings:
    """Hard limits that the future deterministic risk gate must enforce."""

    risk_per_trade: float
    max_daily_loss: float
    max_open_positions: int
    max_spread_points: int
    max_position_size: float
    require_stop_loss: bool
    require_take_profit: bool
    broker_lot_constraints_source: str


@dataclass(frozen=True, slots=True)
class TradingSessionSettings:
    """Timezone-aware session contract; broker timezone is intentionally external."""

    timezone: str
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class MT5ConnectionSettings:
    """Non-secret MT5 connectivity settings; credentials stay outside this file."""

    terminal_path: str | None
    login_env_var: str
    server_env_var: str
    password_env_var: str
    connection_timeout_seconds: int
    data_freshness_seconds: int


@dataclass(frozen=True, slots=True)
class LLMSettings:
    """TradingAgents-compatible provider and model selection."""

    provider: str
    deep_think_model: str
    quick_think_model: str
    backend_url: str | None


@dataclass(frozen=True, slots=True)
class AuditLoggingSettings:
    """Required fields for the append-only decision and execution audit trail."""

    journal_path: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ForexMT5DemoSettings:
    """Complete Phase-1 USD/JPY M1 demo configuration contract."""

    instrument: ForexInstrumentSettings
    execution: DemoExecutionSettings
    risk: ForexRiskSettings
    session: TradingSessionSettings
    mt5: MT5ConnectionSettings
    llm: LLMSettings
    logging: AuditLoggingSettings


def load_settings(path: Path) -> Settings:
    """Load a TOML profile and reject an unsafe live-trading setting."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    runtime = RuntimeSettings(**raw["runtime"])
    risk = RiskSettings(**raw["risk"])
    if runtime.live_trading_enabled:
        raise ValueError("live trading cannot be enabled by a base configuration")
    for value in (
        risk.risk_per_trade,
        risk.max_daily_drawdown,
        risk.max_total_drawdown,
        risk.max_correlated_open_risk,
    ):
        if not 0 < value <= 1:
            raise ValueError("risk fractions must be greater than zero and at most one")
    return Settings(runtime=runtime, risk=risk)


_REQUIRED_AUDIT_FIELDS = frozenset(
    {
        "candle_timestamp",
        "market_snapshot",
        "agent_decision",
        "trade_intent",
        "risk_decision",
        "execution_result",
        "broker_ticket",
        "position_state",
    }
)


def _table(raw: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = raw.get(name)
    if not isinstance(value, Mapping):
        raise ForexMT5DemoConfigurationError(f"{name} must be a TOML table")
    return value


def _string(table: Mapping[str, Any], name: str) -> str:
    value = table.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ForexMT5DemoConfigurationError(f"{name} must be a non-empty string")
    return value


def _boolean(table: Mapping[str, Any], name: str) -> bool:
    value = table.get(name)
    if not isinstance(value, bool):
        raise ForexMT5DemoConfigurationError(f"{name} must be a boolean")
    return value


def _integer(table: Mapping[str, Any], name: str, minimum: int = 0) -> int:
    value = table.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ForexMT5DemoConfigurationError(f"{name} must be an integer >= {minimum}")
    return value


def _fraction(table: Mapping[str, Any], name: str) -> float:
    value = table.get(name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 < value <= 1
    ):
        raise ForexMT5DemoConfigurationError(
            f"{name} must be greater than zero and at most one"
        )
    return float(value)


def load_xauusd_read_only_broker_profile(path: Path) -> XAUUSDReadOnlyBrokerProfile:
    """Load an observed-only XAUUSD contract with no inherited risk defaults."""
    with path.open("rb") as file:
        raw = tomllib.load(file)
    instrument = _table(raw, "instrument")
    account = _table(raw, "account")
    execution = _table(raw, "execution")
    logging = _table(raw, "logging")
    unresolved = logging.get("unresolved_requirements")
    if not isinstance(unresolved, list) or not all(
        isinstance(item, str) and item for item in unresolved
    ):
        raise ForexMT5DemoConfigurationError("unresolved_requirements must be strings")
    required_unresolved = {
        "maximum_spread_policy",
        "risk_sizing_formula",
        "maximum_position_size",
        "execution_deviation",
        "stop_freeze_levels",
        "trading_session_policy",
    }
    if set(unresolved) != required_unresolved:
        raise ForexMT5DemoConfigurationError(
            "XAUUSD unresolved requirements are incomplete"
        )
    if "risk" in raw or "session" in raw:
        raise ForexMT5DemoConfigurationError(
            "XAUUSD broker profile cannot inherit risk or session policy"
        )
    profile = XAUUSDReadOnlyBrokerProfile(
        internal_symbol=_string(instrument, "internal_symbol"),
        broker_symbol=_string(instrument, "broker_symbol"),
        timeframe=_string(instrument, "timeframe"),
        account_currency=_string(account, "currency"),
        demo_only=_boolean(account, "demo_only"),
        order_submission_enabled=_boolean(execution, "order_submission_enabled"),
        audit_journal_path=_string(logging, "audit_journal_path"),
        unresolved_requirements=tuple(unresolved),
    )
    if (
        profile.internal_symbol != "XAUUSD"
        or profile.broker_symbol != "XAUUSD"
        or profile.timeframe != "M1"
        or profile.account_currency != "USD"
        or not profile.demo_only
        or profile.order_submission_enabled
    ):
        raise ForexMT5DemoConfigurationError(
            "XAUUSD read-only broker contract is invalid"
        )
    observed_broker_fields = {
        "digits",
        "point",
        "contract_size",
        "volume_min",
        "volume_max",
        "volume_step",
    }
    if observed_broker_fields.intersection(instrument) or "filling_mode" in execution:
        raise ForexMT5DemoConfigurationError(
            "XAUUSD broker facts must be observed through the read-only MT5 bridge"
        )
    if "usdjpy" in profile.audit_journal_path.lower():
        raise ForexMT5DemoConfigurationError(
            "XAUUSD audit scope must be separate from USDJPY"
        )
    return profile


def load_forex_mt5_demo_settings(path: Path) -> ForexMT5DemoSettings:
    """Load the Phase-1 USD/JPY profile and reject unsafe or incomplete settings.

    This function intentionally provides no live-mode escape hatch. A later,
    explicitly authorised execution phase will need a separately reviewed
    configuration type and cannot reuse this demo profile to enable live orders.
    """
    with path.open("rb") as file:
        raw = tomllib.load(file)

    instrument_raw = _table(raw, "instrument")
    internal_symbol = _string(instrument_raw, "internal_symbol")
    if internal_symbol != "USDJPY":
        raise ForexMT5DemoConfigurationError(
            "internal_symbol must be USDJPY for this profile"
        )
    instrument = ForexInstrumentSettings(
        internal_symbol=internal_symbol,
        broker_symbol=_string(instrument_raw, "broker_symbol"),
        timeframe=_string(instrument_raw, "timeframe"),
        closed_candles_only=_boolean(instrument_raw, "closed_candles_only"),
    )
    if instrument.timeframe != "M1":
        raise ForexMT5DemoConfigurationError("timeframe must be M1")
    if not instrument.closed_candles_only:
        raise ForexMT5DemoConfigurationError("closed_candles_only must be true")

    execution_raw = _table(raw, "execution")
    execution = DemoExecutionSettings(
        account_mode=_string(execution_raw, "account_mode"),
        live_trading_enabled=_boolean(execution_raw, "live_trading_enabled"),
        order_submission_enabled=_boolean(execution_raw, "order_submission_enabled"),
        magic_number=_integer(execution_raw, "magic_number", minimum=1),
        deviation_points=_integer(execution_raw, "deviation_points"),
        filling_mode=_string(execution_raw, "filling_mode"),
    )
    if execution.account_mode != "demo":
        raise ForexMT5DemoConfigurationError("account_mode must be demo")
    if execution.live_trading_enabled:
        raise ForexMT5DemoConfigurationError(
            "live trading is prohibited by the demo profile"
        )
    if execution.order_submission_enabled:
        raise ForexMT5DemoConfigurationError("Phase 1 cannot enable order submission")

    risk_raw = _table(raw, "risk")
    risk = ForexRiskSettings(
        risk_per_trade=_fraction(risk_raw, "risk_per_trade"),
        max_daily_loss=_fraction(risk_raw, "max_daily_loss"),
        max_open_positions=_integer(risk_raw, "max_open_positions", minimum=1),
        max_spread_points=_integer(risk_raw, "max_spread_points", minimum=1),
        max_position_size=float(risk_raw.get("max_position_size", 0)),
        require_stop_loss=_boolean(risk_raw, "require_stop_loss"),
        require_take_profit=_boolean(risk_raw, "require_take_profit"),
        broker_lot_constraints_source=_string(
            risk_raw, "broker_lot_constraints_source"
        ),
    )
    if risk.max_open_positions != 1:
        raise ForexMT5DemoConfigurationError("max_open_positions must be exactly one")
    if risk.max_position_size <= 0:
        raise ForexMT5DemoConfigurationError(
            "max_position_size must be greater than zero"
        )
    if not risk.require_stop_loss or not risk.require_take_profit:
        raise ForexMT5DemoConfigurationError(
            "stop loss and take profit must both be mandatory"
        )
    if risk.broker_lot_constraints_source != "mt5_symbol_info":
        raise ForexMT5DemoConfigurationError(
            "broker lot constraints must be read from mt5_symbol_info"
        )

    session_raw = _table(raw, "session")
    session = TradingSessionSettings(
        timezone=_string(session_raw, "timezone"),
        start=_string(session_raw, "start"),
        end=_string(session_raw, "end"),
    )
    try:
        ZoneInfo(session.timezone)
    except ZoneInfoNotFoundError as error:
        raise ForexMT5DemoConfigurationError(
            "session timezone must be an explicit IANA timezone"
        ) from error

    mt5_raw = _table(raw, "mt5")
    terminal_path_value = mt5_raw.get("terminal_path")
    if terminal_path_value is not None and not isinstance(terminal_path_value, str):
        raise ForexMT5DemoConfigurationError(
            "terminal_path must be a string or omitted"
        )
    mt5 = MT5ConnectionSettings(
        terminal_path=terminal_path_value or None,
        login_env_var=_string(mt5_raw, "login_env_var"),
        server_env_var=_string(mt5_raw, "server_env_var"),
        password_env_var=_string(mt5_raw, "password_env_var"),
        connection_timeout_seconds=_integer(
            mt5_raw, "connection_timeout_seconds", minimum=1
        ),
        data_freshness_seconds=_integer(mt5_raw, "data_freshness_seconds", minimum=1),
    )

    llm_raw = _table(raw, "llm")
    backend_url = llm_raw.get("backend_url")
    if backend_url is not None and not isinstance(backend_url, str):
        raise ForexMT5DemoConfigurationError("backend_url must be a string or omitted")
    llm = LLMSettings(
        provider=_string(llm_raw, "provider"),
        deep_think_model=_string(llm_raw, "deep_think_model"),
        quick_think_model=_string(llm_raw, "quick_think_model"),
        backend_url=backend_url,
    )

    logging_raw = _table(raw, "logging")
    required_fields_raw = logging_raw.get("required_fields")
    if not isinstance(required_fields_raw, list) or not all(
        isinstance(item, str) for item in required_fields_raw
    ):
        raise ForexMT5DemoConfigurationError(
            "logging.required_fields must be a list of strings"
        )
    required_fields = tuple(required_fields_raw)
    missing_fields = _REQUIRED_AUDIT_FIELDS.difference(required_fields)
    if missing_fields:
        raise ForexMT5DemoConfigurationError(
            f"logging.required_fields is missing: {', '.join(sorted(missing_fields))}"
        )
    logging = AuditLoggingSettings(
        journal_path=_string(logging_raw, "journal_path"),
        required_fields=required_fields,
    )

    return ForexMT5DemoSettings(instrument, execution, risk, session, mt5, llm, logging)
