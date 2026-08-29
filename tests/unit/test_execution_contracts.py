"""Unit tests for MT5 Execution Contracts and AutoExecutionQueue."""

from quantforge.infrastructure.mt5.auto_execution_service import AutoExecutionQueue
from quantforge.infrastructure.mt5.execution_contracts import (
    ExecutionReceipt,
    OrderRequest,
)


def test_order_request_serialization() -> None:
    order = OrderRequest(
        order_id="ord-123",
        symbol="#BTCUSD",
        side="buy",
        volume=0.1,
        order_type="market",
        price=77650.0,
        stop_loss=77600.0,
        take_profit=77750.0,
        magic_number=7007,
    )
    payload = order.to_payload()
    assert payload["order_id"] == "ord-123"
    assert payload["symbol"] == "#BTCUSD"
    assert payload["side"] == "buy"
    assert payload["magic_number"] == 7007

    recovered = OrderRequest.from_payload(payload)
    assert recovered.order_id == "ord-123"
    assert recovered.volume == 0.1
    assert recovered.stop_loss == 77600.0


def test_execution_receipt_serialization() -> None:
    receipt = ExecutionReceipt(
        order_id="ord-123",
        broker_ticket=998877,
        executed_price=77650.25,
        executed_volume=0.1,
        status="FILLED",
    )
    payload = receipt.to_payload()
    assert payload["broker_ticket"] == 998877
    assert payload["status"] == "FILLED"

    recovered = ExecutionReceipt.from_payload(payload)
    assert recovered.broker_ticket == 998877
    assert recovered.status == "FILLED"


def test_auto_execution_queue_flow() -> None:
    queue = AutoExecutionQueue()
    assert queue.auto_trading_enabled

    order = OrderRequest(
        order_id="ord-001",
        symbol="BTCUSD",
        side="buy",
        volume=0.05,
        order_type="market",
        price=77600.0,
        stop_loss=77550.0,
        take_profit=77700.0,
    )
    assert queue.enqueue_order(order)
    assert len(queue.peek_pending_orders()) == 1

    popped = queue.pop_pending_orders()
    assert len(popped) == 1
    assert popped[0].order_id == "ord-001"
    assert len(queue.peek_pending_orders()) == 0

    # Test receipt recording
    receipt = ExecutionReceipt(
        order_id="ord-001",
        broker_ticket=123456,
        executed_price=77600.10,
        executed_volume=0.05,
        status="FILLED",
    )
    queue.record_receipt(receipt)
    rec = queue.get_receipt("ord-001")
    assert rec is not None
    assert rec.broker_ticket == 123456
    assert rec.status == "FILLED"
