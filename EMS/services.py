import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from EMS.models import (
    ACRRecord,
    Designation,
    DigitalSignature,
    EmployeeServiceSnapshot,
    PayScale,
    ProbationRecord,
    ServiceEvent,
    TransferWorkflow,
    audit_change,
)
from EMS.validators import validate_service_event


def employee_cen(employee):
    if isinstance(employee, str):
        value = employee
    else:
        field = getattr(settings, "SERVICE_BOOK_EMPLOYEE_CEN_FIELD", "cen")
        value = getattr(employee, field, None)
        if value is None:
            for candidate in ("CEN", "employee_cen"):
                value = getattr(employee, candidate, None)
                if value is not None:
                    break
        if value is None:
            raise ValidationError(
                f"Employee must expose its CEN value through {field!r}; configure "
                "SERVICE_BOOK_EMPLOYEE_CEN_FIELD for the shared Employee model."
            )
    value = str(value).strip()
    if not value:
        raise ValidationError("Employee CEN must not be empty.")
    return value


class DigitalSignatureBackend(Protocol):
    def sign(self, *, event: ServiceEvent, signer: str) -> tuple[str, str]: ...


class DummyDigitalSignature:
    provider = "dummy-sha256"

    def sign(self, *, event: ServiceEvent, signer: str) -> tuple[str, str]:
        contents = json.dumps(
            {
                "event_id": event.pk,
                "employee_cen": event.employee_cen,
                "event_type": event.event_type,
                "effective_date": event.effective_date.isoformat(),
                "payload": event.payload,
                "signer": signer,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return self.provider, hashlib.sha256(contents.encode("utf-8")).hexdigest()


def _approved_events(cen, *, through_date=None):
    events = ServiceEvent.objects.filter(
        employee_cen=cen,
        status__in=(ServiceEvent.Status.APPROVED, ServiceEvent.Status.CANCELLED),
    ).order_by("effective_date", "approved_at", "pk")
    if through_date is not None:
        events = events.filter(effective_date__lte=through_date)
    return [
        event for event in events
        if event.status == ServiceEvent.Status.APPROVED
        or event.cancelled_on is None
        or (through_date is not None and through_date < event.cancelled_on)
    ]


def _empty_state(cen, as_of):
    return {
        "employee_cen": cen,
        "as_of_date": as_of,
        "designation_id": None,
        "designation_code": "",
        "designation_name": "",
        "designation_description": "",
        "designation_level": None,
        "pay_scale_id": None,
        "pay_scale_code": "",
        "pay_scale_min_pay": None,
        "pay_scale_max_pay": None,
        "pay_scale_revision_order": None,
        "pay_scale_effective_date": None,
        "pay_scale_increment_steps": [],
        "current_pay": None,
        "society_cen": "",
        "employment_status": "ACTIVE",
        "probation_status": "",
        "leave_end_date": None,
        "event_ids": [],
    }


def _apply_event(state, event):
    data = event.payload
    kind = event.event_type
    if kind in ("APPOINTMENT", "PROMOTION", "DESIGNATION_CHANGE"):
        state["designation_id"] = data.get("designation_id")
        state["designation_code"] = data.get("designation_code_snapshot", "")
        state["designation_name"] = data.get("designation_name_snapshot", "")
        state["designation_description"] = data.get("designation_description_snapshot", "")
        state["designation_level"] = data.get("designation_level_snapshot")
        if data.get("pay_scale_id") is not None:
            state["pay_scale_id"] = data["pay_scale_id"]
            state["pay_scale_code"] = data.get("pay_scale_code_snapshot", "")
            state["pay_scale_min_pay"] = Decimal(data["pay_scale_min_pay_snapshot"])
            state["pay_scale_max_pay"] = Decimal(data["pay_scale_max_pay_snapshot"])
            state["pay_scale_revision_order"] = data["pay_scale_revision_order_snapshot"]
            state["pay_scale_effective_date"] = date.fromisoformat(data["pay_scale_effective_date_snapshot"])
            state["pay_scale_increment_steps"] = data["pay_scale_increment_steps_snapshot"]
        amount = data.get("pay_amount")
        if amount is not None:
            state["current_pay"] = Decimal(str(amount))
        if kind == "APPOINTMENT":
            state["society_cen"] = data.get("society_cen", "")
            state["employment_status"] = "ACTIVE"
            state["probation_status"] = "PROBATION"
    elif kind == "INCREMENT":
        state["pay_scale_id"] = data["pay_scale_id"]
        state["pay_scale_code"] = data.get("pay_scale_code_snapshot", "")
        state["pay_scale_min_pay"] = Decimal(data["pay_scale_min_pay_snapshot"])
        state["pay_scale_max_pay"] = Decimal(data["pay_scale_max_pay_snapshot"])
        state["pay_scale_revision_order"] = data["pay_scale_revision_order_snapshot"]
        state["pay_scale_effective_date"] = date.fromisoformat(data["pay_scale_effective_date_snapshot"])
        state["pay_scale_increment_steps"] = data["pay_scale_increment_steps_snapshot"]
        state["current_pay"] = Decimal(str(data["new_pay"]))
    elif kind == "PAY_REVISION":
        state["pay_scale_id"] = data["pay_scale_id"]
        state["pay_scale_code"] = data.get("pay_scale_code_snapshot", "")
        state["pay_scale_min_pay"] = Decimal(data["pay_scale_min_pay_snapshot"])
        state["pay_scale_max_pay"] = Decimal(data["pay_scale_max_pay_snapshot"])
        state["pay_scale_revision_order"] = data["pay_scale_revision_order_snapshot"]
        state["pay_scale_effective_date"] = date.fromisoformat(data["pay_scale_effective_date_snapshot"])
        state["pay_scale_increment_steps"] = data["pay_scale_increment_steps_snapshot"]
        state["current_pay"] = Decimal(str(data["pay_amount"]))
    elif kind == "TRANSFER":
        state["society_cen"] = data.get("to_society_cen", "")
    elif kind == "PROBATION_CONFIRMED":
        state["probation_status"] = "CONFIRMED"
    elif kind == "PROBATION_EXTENDED":
        state["probation_status"] = "EXTENDED"
    elif kind == "SUSPENSION":
        state["employment_status"] = "SUSPENDED"
    elif kind == "REINSTATEMENT":
        state["employment_status"] = "ACTIVE"
    elif kind == "TERMINATION":
        state["employment_status"] = "TERMINATED"
    elif kind == "LEAVE":
        state["employment_status"] = "ON_LEAVE"
        state["leave_end_date"] = date.fromisoformat(data["end_date"])
    state["event_ids"].append(event.pk)


def state_as_of(employee, as_of_date):
    cen = employee_cen(employee)
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()
    if not isinstance(as_of_date, date):
        raise ValidationError({"date": "Provide a valid date for the historical state query."})
    state = _empty_state(cen, as_of_date)
    for event in _approved_events(cen, through_date=as_of_date):
        _apply_event(state, event)
    if state["employment_status"] == "ON_LEAVE" and as_of_date > state["leave_end_date"]:
        state["employment_status"] = "ACTIVE"
    return state


def _state_before(event):
    return state_as_of(event.employee_cen, date.fromordinal(event.effective_date.toordinal() - 1))


def _check_business_rules(event):
    validate_service_event(event)
    state = _state_before(event)
    data = event.payload
    kind = event.event_type
    scale_id = data.get("pay_scale_id")
    if scale_id is not None:
        scale = PayScale.objects.get(pk=scale_id)
        if scale.effective_date > event.effective_date:
            raise ValidationError({"pay_scale_id": "Pay scale is not effective on the event date."})
        if not scale.is_active:
            raise ValidationError({"pay_scale_id": "Inactive pay scales cannot be used for new service events."})
    if kind == "APPOINTMENT":
        if state["designation_id"] is not None:
            raise ValidationError("An employee with an existing appointment cannot be appointed again.")
        designation = Designation.objects.get(pk=data["designation_id"])
        scale = PayScale.objects.get(pk=data["pay_scale_id"])
        if not designation.is_active:
            raise ValidationError({"designation_id": "Inactive designations cannot be used for new appointments."})
        if not scale.effective_date <= event.effective_date:
            raise ValidationError({"pay_scale_id": "Pay scale is not effective on the appointment date."})
    elif kind in ("PROMOTION", "DESIGNATION_CHANGE"):
        if state["designation_id"] is None:
            raise ValidationError("Designation changes require a prior approved appointment.")
        if state["employment_status"] != "ACTIVE":
            raise ValidationError("Designation changes require an active employee.")
        target = Designation.objects.get(pk=data["designation_id"])
        if not target.is_active:
            raise ValidationError({"designation_id": "Inactive designations cannot be assigned."})
        if kind == "PROMOTION":
            prior_level = state["designation_level"]
            if prior_level is None or target.level <= prior_level:
                raise ValidationError({"designation_id": "A promotion must move to a higher designation level."})
        if data.get("pay_amount") is not None:
            pay_scale_id = data.get("pay_scale_id") or state["pay_scale_id"]
            if pay_scale_id is None:
                raise ValidationError({"pay_scale_id": "A pay scale is required when setting designation pay."})
            scale = PayScale.objects.get(pk=pay_scale_id)
            amount = Decimal(str(data["pay_amount"]))
            if not scale.min_pay <= amount <= scale.max_pay:
                raise ValidationError({"pay_amount": "Designation pay must be within the selected pay scale."})
    elif kind == "INCREMENT":
        if state["current_pay"] is None or state["pay_scale_id"] is None:
            raise ValidationError("An increment requires an existing approved pay and pay scale.")
        if state["employment_status"] != "ACTIVE":
            raise ValidationError("An increment requires an active employee.")
        if str(state["pay_scale_id"]) != str(data["pay_scale_id"]):
            raise ValidationError({"pay_scale_id": "Use the current pay scale for an increment."})
        expected = state["current_pay"] + Decimal(str(data["increment_amount"]))
        if expected != Decimal(str(data["new_pay"])):
            raise ValidationError({"new_pay": f"New pay must equal {expected}."})
        scale = PayScale.objects.get(pk=data["pay_scale_id"])
        if expected > scale.max_pay:
            raise ValidationError({"new_pay": "Increment would exceed the pay-scale maximum."})
    elif kind == "PAY_REVISION":
        if state["designation_id"] is None:
            raise ValidationError("A pay revision requires a prior approved appointment.")
        if state["employment_status"] != "ACTIVE":
            raise ValidationError("A pay revision requires an active employee.")
    elif kind == "TRANSFER":
        if not state["society_cen"]:
            raise ValidationError("Transfer requires a current society from an approved appointment or transfer.")
        if state["employment_status"] != "ACTIVE":
            raise ValidationError("Transfer requires an active employee.")
        workflow = getattr(event, "transfer_workflow", None)
        if not workflow or workflow.status != TransferWorkflow.Status.ACCEPTED:
            raise ValidationError("Both relieving and receiving societies must accept the transfer.")
        if workflow.from_society_cen != state["society_cen"]:
            raise ValidationError({"from_society_cen": "Relieving society does not match the employee's current society."})
        if data["to_society_cen"] != workflow.to_society_cen:
            raise ValidationError({"to_society_cen": "Receiving society does not match transfer acceptance."})
    elif kind == "PROBATION_CONFIRMED":
        record = ProbationRecord.objects.filter(
            employee_cen=event.employee_cen,
            status__in=(ProbationRecord.Status.ACTIVE, ProbationRecord.Status.EXTENDED),
        ).order_by("-start_date").first()
        if not record:
            raise ValidationError("Probation confirmation requires an active probation record.")
        if event.effective_date < record.start_date:
            raise ValidationError({"effective_date": "Probation cannot be confirmed before it starts."})
    elif kind == "PROBATION_EXTENDED":
        record = ProbationRecord.objects.filter(
            employee_cen=event.employee_cen,
            status__in=(ProbationRecord.Status.ACTIVE, ProbationRecord.Status.EXTENDED),
        ).order_by("-start_date").first()
        if not record:
            raise ValidationError("Probation extension requires an active probation record.")
        new_end = date.fromisoformat(data["new_end_date"])
        if new_end <= record.expected_end_date:
            raise ValidationError({"new_end_date": "Extended end date must be later than the current end date."})
        if new_end <= event.effective_date:
            raise ValidationError({"new_end_date": "Extended probation must end after the event date."})
    elif kind == "SUSPENSION" and (
        state["designation_id"] is None or state["employment_status"] != "ACTIVE"
    ):
        raise ValidationError("Only an appointed active employee can be suspended.")
    elif kind == "REINSTATEMENT" and state["employment_status"] != "SUSPENDED":
        raise ValidationError("Reinstatement requires a prior suspension.")
    elif kind == "TERMINATION" and (
        state["designation_id"] is None or state["employment_status"] != "ACTIVE"
    ):
        raise ValidationError("Only an appointed active employee can be terminated.")
    elif kind == "LEAVE" and (
        state["designation_id"] is None or state["employment_status"] != "ACTIVE"
    ):
        raise ValidationError("Leave requires an appointed active employee.")
    return state


def _capture_historical_catalog_values(event):
    data = dict(event.payload)
    designation_id = data.get("designation_id")
    if designation_id is not None:
        designation = Designation.objects.get(pk=designation_id)
        event.designation = designation
        data.update(
            designation_code_snapshot=designation.code,
            designation_name_snapshot=designation.name,
            designation_description_snapshot=designation.description,
            designation_level_snapshot=designation.level,
        )
    scale_id = data.get("pay_scale_id")
    if scale_id is not None:
        scale = PayScale.objects.get(pk=scale_id)
        event.pay_scale = scale
        data.update(
            pay_scale_code_snapshot=scale.code,
            pay_scale_min_pay_snapshot=str(scale.min_pay),
            pay_scale_max_pay_snapshot=str(scale.max_pay),
            pay_scale_revision_order_snapshot=scale.revision_order,
            pay_scale_effective_date_snapshot=scale.effective_date.isoformat(),
            pay_scale_increment_steps_snapshot=scale.increment_steps,
        )
    event.payload = data


def _capture_probation_previous_state(event):
    if event.event_type not in ("PROBATION_CONFIRMED", "PROBATION_EXTENDED"):
        return
    record = ProbationRecord.objects.filter(
        employee_cen=event.employee_cen,
        status__in=(ProbationRecord.Status.ACTIVE, ProbationRecord.Status.EXTENDED),
    ).order_by("-start_date").first()
    if record:
        event.payload = {
            **event.payload,
            "_probation_record_id": record.pk,
            "_probation_previous_status": record.status,
            "_probation_previous_end": record.expected_end_date.isoformat(),
            "_probation_previous_reason": record.extension_reason,
        }


def _apply_probation_event(event):
    if event.event_type == "PROBATION_CONFIRMED":
        record = ProbationRecord.objects.filter(
            pk=event.payload.get("_probation_record_id"),
            employee_cen=event.employee_cen,
        ).first()
        record.status = ProbationRecord.Status.CONFIRMED
        record.actual_end_date = event.effective_date
        record.confirmation_event = event
        record.save()
    elif event.event_type == "PROBATION_EXTENDED":
        record = ProbationRecord.objects.filter(
            pk=event.payload.get("_probation_record_id"),
            employee_cen=event.employee_cen,
        ).first()
        record.expected_end_date = date.fromisoformat(event.payload["new_end_date"])
        record.extension_reason = event.payload["reason"]
        record.status = ProbationRecord.Status.EXTENDED
        record.save()


def _reverse_probation_event(event):
    if event.event_type not in ("PROBATION_CONFIRMED", "PROBATION_EXTENDED"):
        return
    later_event_exists = ServiceEvent.objects.filter(
        employee_cen=event.employee_cen,
        event_type__in=("PROBATION_CONFIRMED", "PROBATION_EXTENDED"),
        status=ServiceEvent.Status.APPROVED,
        effective_date__gt=event.effective_date,
    ).exists()
    if later_event_exists:
        return
    record = ProbationRecord.objects.filter(
        pk=event.payload.get("_probation_record_id"),
        employee_cen=event.employee_cen,
    ).first()
    if not record:
        return
    record.status = event.payload["_probation_previous_status"]
    record.expected_end_date = date.fromisoformat(event.payload["_probation_previous_end"])
    record.extension_reason = event.payload.get("_probation_previous_reason", "")
    record.actual_end_date = None
    record.confirmation_event = None
    record.save()


@transaction.atomic
def submit_event(event, *, actor=None):
    if event.status != ServiceEvent.Status.DRAFT:
        raise ValidationError("Only draft service events can be submitted.")
    if event.is_locked:
        raise ValidationError("Unlock the service event before submitting it.")
    event.full_clean()
    if event.event_type == "TRANSFER":
        state = _state_before(event)
        from_society = state["society_cen"]
        if not from_society:
            raise ValidationError("Transfer requires an existing society assignment.")
        to_society = str(event.payload["to_society_cen"]).strip()
        if from_society == to_society:
            raise ValidationError({"to_society_cen": "Receiving society must differ from current society."})
    event.status = ServiceEvent.Status.SUBMITTED
    event.submitted_at = timezone.now()
    event.save(update_fields=("status", "submitted_at"))
    if event.event_type == "TRANSFER":
        TransferWorkflow.objects.create(
            event=event,
            from_society_cen=from_society,
            to_society_cen=to_society,
        )
    audit_change(
        employee_cen=event.employee_cen, instance=event, action="submitted",
        actor=actor, changes={"status": event.status},
    )
    return event


def _sign_event(event, actor):
    signer = str(actor) if actor else "system"
    backend: DigitalSignatureBackend = DummyDigitalSignature()
    provider, signature = backend.sign(event=event, signer=signer)
    DigitalSignature.objects.update_or_create(
        event=event,
        defaults={"provider": provider, "signer": signer, "signature_value": signature},
    )


@transaction.atomic
def approve_event(event, *, actor=None):
    event = ServiceEvent.objects.select_for_update().get(pk=event.pk)
    if event.status != ServiceEvent.Status.SUBMITTED:
        raise ValidationError("Only submitted service events can be approved.")
    if event.is_locked:
        raise ValidationError("Unlock the service event before approving it.")
    _check_business_rules(event)
    _capture_probation_previous_state(event)
    _capture_historical_catalog_values(event)
    event.status = ServiceEvent.Status.APPROVED
    event.approved_by = actor
    event.approved_at = timezone.now()
    event.save()
    _apply_probation_event(event)
    _sign_event(event, actor)
    audit_change(
        employee_cen=event.employee_cen, instance=event, action="approved",
        actor=actor, changes={"status": event.status, "payload": event.payload},
    )
    ServiceBookService.rebuild(event.employee_cen)
    return event


@transaction.atomic
def cancel_event(event, *, actor=None, reason):
    event = ServiceEvent.objects.select_for_update().get(pk=event.pk)
    if event.status not in (ServiceEvent.Status.DRAFT, ServiceEvent.Status.SUBMITTED, ServiceEvent.Status.APPROVED):
        raise ValidationError("This service event is already cancelled.")
    if event.is_locked:
        raise ValidationError("Unlock the service event before cancelling it.")
    if not reason.strip():
        raise ValidationError({"reason": "A cancellation reason is required."})
    if event.status == ServiceEvent.Status.APPROVED:
        history = _approved_events(event.employee_cen)
        position = next((index for index, item in enumerate(history) if item.pk == event.pk), None)
        if position is not None and position < len(history) - 1:
            raise ValidationError(
                "Cancel later approved events first so service history remains consistent."
            )
    now = timezone.now()
    if event.status == ServiceEvent.Status.APPROVED:
        _reverse_probation_event(event)
        if event.event_type == "APPOINTMENT":
            ProbationRecord.objects.filter(
                employee_cen=event.employee_cen,
                status__in=(ProbationRecord.Status.ACTIVE, ProbationRecord.Status.EXTENDED),
            ).update(status=ProbationRecord.Status.CANCELLED)
    ServiceEvent.objects.filter(pk=event.pk).update(
        status=ServiceEvent.Status.CANCELLED,
        cancelled_at=now,
        cancelled_on=timezone.localdate(now),
        cancellation_reason=reason.strip(),
    )
    if event.event_type == "TRANSFER":
        TransferWorkflow.objects.filter(event=event).update(status=TransferWorkflow.Status.CANCELLED)
    event.refresh_from_db()
    audit_change(
        employee_cen=event.employee_cen, instance=event, action="cancelled",
        actor=actor, changes={"reason": reason.strip()},
    )
    ServiceBookService.rebuild(event.employee_cen)
    return event


def set_event_lock(event, *, locked, actor=None):
    if event.status != ServiceEvent.Status.APPROVED:
        raise ValidationError("Only approved service events can be locked or unlocked.")
    ServiceEvent.objects.filter(pk=event.pk).update(is_locked=locked)
    event.refresh_from_db()
    audit_change(
        employee_cen=event.employee_cen, instance=event,
        action="locked" if locked else "unlocked", actor=actor,
        changes={"is_locked": locked},
    )
    return event


def relieve_transfer(workflow, *, actor=None):
    workflow = TransferWorkflow.objects.select_related("event").get(pk=workflow.pk)
    if workflow.event.status != ServiceEvent.Status.SUBMITTED:
        raise ValidationError("Transfer must be submitted before relieving.")
    if workflow.status != TransferWorkflow.Status.PENDING_RELIEF:
        raise ValidationError("Transfer is not awaiting relieving-society acceptance.")
    workflow.status = TransferWorkflow.Status.RELIEVED
    workflow.relieved_at = timezone.now()
    workflow.relieved_by = actor
    workflow.save(update_fields=("status", "relieved_at", "relieved_by"))
    audit_change(
        employee_cen=workflow.event.employee_cen, instance=workflow,
        action="transfer_relieved", actor=actor,
        changes={"from_society_cen": workflow.from_society_cen},
    )
    return workflow


def accept_transfer(workflow, *, actor=None):
    workflow = TransferWorkflow.objects.select_related("event").get(pk=workflow.pk)
    if workflow.event.status != ServiceEvent.Status.SUBMITTED:
        raise ValidationError("Transfer must be submitted before acceptance.")
    if workflow.status != TransferWorkflow.Status.RELIEVED:
        raise ValidationError("The relieving society must accept before the receiving society.")
    workflow.status = TransferWorkflow.Status.ACCEPTED
    workflow.accepted_at = timezone.now()
    workflow.accepted_by = actor
    workflow.save(update_fields=("status", "accepted_at", "accepted_by"))
    audit_change(
        employee_cen=workflow.event.employee_cen, instance=workflow,
        action="transfer_accepted", actor=actor,
        changes={"to_society_cen": workflow.to_society_cen},
    )
    return workflow


class ServiceBookService:
    @staticmethod
    def rebuild(employee):
        cen = employee_cen(employee)
        state = state_as_of(cen, timezone.localdate())
        designation = Designation.objects.filter(pk=state["designation_id"]).first()
        scale = PayScale.objects.filter(pk=state["pay_scale_id"]).first()
        snapshot, _ = EmployeeServiceSnapshot.objects.update_or_create(
            employee_cen=cen,
            defaults={
                "designation": designation,
                "designation_code": state["designation_code"],
                "designation_name": state["designation_name"],
                "designation_description": state["designation_description"],
                "designation_level": state["designation_level"],
                "pay_scale": scale,
                "pay_scale_code": state["pay_scale_code"],
                "pay_scale_min_pay": state["pay_scale_min_pay"],
                "pay_scale_max_pay": state["pay_scale_max_pay"],
                "pay_scale_revision_order": state["pay_scale_revision_order"],
                "pay_scale_effective_date": state["pay_scale_effective_date"],
                "pay_scale_increment_steps": state["pay_scale_increment_steps"],
                "current_pay": state["current_pay"],
                "society_cen": state["society_cen"],
                "employment_status": state["employment_status"],
                "probation_status": state["probation_status"],
                "as_of_date": timezone.localdate(),
            },
        )
        return snapshot

    @staticmethod
    def state_as_of(employee, as_of_date):
        return state_as_of(employee, as_of_date)


def set_acr_lock(record, *, locked, actor=None):
    ACRRecord.objects.filter(pk=record.pk).update(is_locked=locked)
    record.refresh_from_db()
    audit_change(
        employee_cen=record.employee_cen, instance=record,
        action="acr_locked" if locked else "acr_unlocked", actor=actor,
        changes={"is_locked": locked},
    )
    return record
