"""Risk reservations for conditional orders before a position is open."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RiskReservation:
    reservation_id: UUID
    reserved_risk: Decimal
    member_order_ids: frozenset[UUID]


class ConditionalRiskReservations:
    """Reserve maximum-at-risk for an OCO group, never the sum of its peers."""

    def __init__(self) -> None:
        self._reservations: dict[UUID, RiskReservation] = {}
        self._order_reservations: dict[UUID, UUID] = {}

    def reserve_oco(
        self, reservation_id: UUID, order_risks: dict[UUID, Decimal]
    ) -> RiskReservation:
        if not order_risks or any(risk <= 0 for risk in order_risks.values()):
            raise ValueError("OCO reservation requires positive risk for every order")
        if reservation_id in self._reservations:
            raise ValueError("risk reservation ID must be unique")
        if any(order_id in self._order_reservations for order_id in order_risks):
            raise ValueError("an order already has a conditional risk reservation")
        reservation = RiskReservation(
            reservation_id=reservation_id,
            reserved_risk=max(order_risks.values()),
            member_order_ids=frozenset(order_risks),
        )
        self._reservations[reservation_id] = reservation
        self._order_reservations.update(
            {order_id: reservation_id for order_id in reservation.member_order_ids}
        )
        return reservation

    def release(self, reservation_id: UUID) -> RiskReservation:
        reservation = self._reservations.pop(reservation_id)
        for order_id in reservation.member_order_ids:
            del self._order_reservations[order_id]
        return reservation

    def reservation_for_order(self, order_id: UUID) -> RiskReservation | None:
        """Return the reservation protecting an order, if it has one."""
        reservation_id = self._order_reservations.get(order_id)
        if reservation_id is None:
            return None
        return self._reservations[reservation_id]

    @property
    def total_reserved_risk(self) -> Decimal:
        return sum(
            (reservation.reserved_risk for reservation in self._reservations.values()),
            start=Decimal("0"),
        )
