from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from EMS.models import Designation, EVENT_TYPES, PayScale


def _decimal(value, field):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: "Enter a valid monetary amount."})
    if not amount.is_finite() or amount < 0:
        raise ValidationError({field: "Amount must be finite and non-negative."})
    return amount


def _catalog(payload, key, model, label, *, required=True):
    value = payload.get(key)
    if value in (None, ""):
        if required:
            raise ValidationError({key: f"{label} is required."})
        return None
    if isinstance(value, bool):
        raise ValidationError({key: f"Select a valid {label.lower()}."})
    try:
        return model.objects.get(pk=value)
    except (model.DoesNotExist, TypeError, ValueError):
        raise ValidationError({key: f"Select a valid {label.lower()}."})


def _date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Use a valid YYYY-MM-DD date."})


def validate_service_event(event):
    if event.event_type not in dict(EVENT_TYPES):
        raise ValidationError({"event_type": "Select a valid service event type."})
    if not isinstance(event.payload, dict):
        raise ValidationError({"payload": "Event details must be a JSON object."})

    data = event.payload
    if event.event_type == "APPOINTMENT":
        _catalog(data, "designation_id", Designation, "Designation")
        scale = _catalog(data, "pay_scale_id", PayScale, "Pay scale")
        _decimal(data.get("pay_amount"), "pay_amount")
        society_cen = data.get("society_cen", "")
        if not isinstance(society_cen, str):
            raise ValidationError({"society_cen": "Society CEN must be a string."})
        society_cen = society_cen.strip()
        if not society_cen:
            raise ValidationError({"society_cen": "Initial society CEN is required."})
        if len(society_cen) > 64:
            raise ValidationError({"society_cen": "Society CEN must be at most 64 characters."})
        data["society_cen"] = society_cen
        amount = _decimal(data["pay_amount"], "pay_amount")
        if scale and not scale.min_pay <= amount <= scale.max_pay:
            raise ValidationError({"pay_amount": "Appointment pay must be within the selected pay scale."})
    elif event.event_type in ("PROMOTION", "DESIGNATION_CHANGE"):
        _catalog(data, "designation_id", Designation, "Designation")
        scale = _catalog(data, "pay_scale_id", PayScale, "Pay scale", required=False)
        amount_value = data.get("pay_amount")
        if amount_value is not None:
            amount = _decimal(amount_value, "pay_amount")
            if scale and not scale.min_pay <= amount <= scale.max_pay:
                raise ValidationError({"pay_amount": "Pay must be within the selected pay scale."})
        elif scale:
            raise ValidationError({"pay_amount": "Pay amount is required when changing the pay scale."})
    elif event.event_type == "INCREMENT":
        scale = _catalog(data, "pay_scale_id", PayScale, "Pay scale")
        amount = _decimal(data.get("increment_amount"), "increment_amount")
        if amount not in {Decimal(str(step)) for step in scale.increment_steps}:
            raise ValidationError({"increment_amount": "Increment must match an allowed pay-scale step."})
        _decimal(data.get("new_pay"), "new_pay")
    elif event.event_type == "PAY_REVISION":
        scale = _catalog(data, "pay_scale_id", PayScale, "Pay scale")
        amount = _decimal(data.get("pay_amount"), "pay_amount")
        if not scale.min_pay <= amount <= scale.max_pay:
            raise ValidationError({"pay_amount": "Revised pay must be within the selected pay scale."})
    elif event.event_type == "TRANSFER":
        society_cen = data.get("to_society_cen", "")
        if not isinstance(society_cen, str):
            raise ValidationError({"to_society_cen": "Society CEN must be a string."})
        society_cen = society_cen.strip()
        if not society_cen:
            raise ValidationError({"to_society_cen": "Receiving society CEN is required."})
        if len(society_cen) > 64:
            raise ValidationError({"to_society_cen": "Society CEN must be at most 64 characters."})
        data["to_society_cen"] = society_cen
    elif event.event_type == "PROBATION_EXTENDED":
        if not str(data.get("new_end_date", "")).strip():
            raise ValidationError({"new_end_date": "A revised probation end date is required."})
        if not str(data.get("reason", "")).strip():
            raise ValidationError({"reason": "A reason is required to extend probation."})
        _date(data["new_end_date"], "new_end_date")
    elif event.event_type == "LEAVE":
        if not str(data.get("start_date", "")).strip() or not str(data.get("end_date", "")).strip():
            raise ValidationError({"start_date": "Leave start and end dates are required."})
        start = _date(data["start_date"], "start_date")
        end = _date(data["end_date"], "end_date")
        if event.effective_date != start:
            raise ValidationError({"effective_date": "Leave event date must match its start date."})
        if end < start:
            raise ValidationError({"end_date": "Leave end date cannot precede its start date."})
    elif event.event_type in ("SUSPENSION", "REINSTATEMENT", "TERMINATION"):
        if not str(data.get("reason", "")).strip():
            raise ValidationError({"reason": "A reason is required for this event."})
