"""Auto Execution Service for MetaTrader 5.

Manages the order queue dispatched from the Risk Gate and serves
pending orders to MT5, reconciling broker execution receipts.
"""

from __future__ import annotations

import collections
import logging
from threading import Lock

from quantforge.infrastructure.mt5.execution_contracts import (
    ExecutionReceipt,
    OrderRequest,
)

logger = logging.getLogger("quantforge.mt5.execution")


class AutoExecutionQueue:
    """Thread-safe queue of authorized trade orders waiting for MT5 execution."""

    def __init__(self, max_size: int = 50) -> None:
        self._lock = Lock()
        self._pending: collections.deque[OrderRequest] = collections.deque(
            maxlen=max_size
        )
        self._history: dict[str, ExecutionReceipt] = {}
        self._auto_trading_enabled: bool = True

    @property
    def auto_trading_enabled(self) -> bool:
        with self._lock:
            return self._auto_trading_enabled

    @auto_trading_enabled.setter
    def auto_trading_enabled(self, value: bool) -> None:
        with self._lock:
            self._auto_trading_enabled = value

    def enqueue_order(self, order: OrderRequest) -> bool:
        """Enqueue an approved order for MT5 execution."""
        with self._lock:
            if not self._auto_trading_enabled:
                logger.warning(
                    f"Order {order.order_id} rejected: Auto-trading is paused."
                )
                return False
            self._pending.append(order)
            logger.info(
                f"Queued order {order.order_id} for {order.symbol} {order.side} {order.volume} lots."
            )
            return True

    def pop_pending_orders(self) -> list[OrderRequest]:
        """Pop all pending orders to deliver to MT5 in a single batch."""
        with self._lock:
            if not self._auto_trading_enabled:
                return []
            orders = list(self._pending)
            self._pending.clear()
            return orders

    def peek_pending_orders(self) -> list[OrderRequest]:
        """View pending orders without dequeuing them."""
        with self._lock:
            return list(self._pending)

    def record_receipt(self, receipt: ExecutionReceipt) -> None:
        """Record the broker's execution receipt and update order history."""
        with self._lock:
            self._history[receipt.order_id] = receipt
            logger.info(
                f"Recorded execution receipt for {receipt.order_id}: "
                f"Status={receipt.status} Ticket={receipt.broker_ticket} Price={receipt.executed_price}"
            )

    def get_receipt(self, order_id: str) -> ExecutionReceipt | None:
        """Retrieve execution receipt by order ID."""
        with self._lock:
            return self._history.get(order_id)

    def clear(self) -> None:
        """Clear all pending orders (e.g. on emergency stop)."""
        with self._lock:
            self._pending.clear()
