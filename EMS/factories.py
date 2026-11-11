from datetime import date
from decimal import Decimal

import factory

from EMS.models import Designation, PayScale


class DesignationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Designation

    code = factory.Sequence(lambda number: f"DESG-{number:04d}")
    name = factory.Sequence(lambda number: f"Designation {number}")
    is_active = True


class PayScaleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PayScale

    code = factory.Sequence(lambda number: f"SCALE-{number:04d}")
    min_pay = Decimal("25000.00")
    max_pay = Decimal("50000.00")
    increment_steps = factory.LazyFunction(lambda: [500, 750])
    revision_order = factory.Sequence(lambda number: number)
    effective_date = date(2026, 1, 1)
