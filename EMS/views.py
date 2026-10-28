
from django.shortcuts import render
from .models import Employee


def employee_list(request):
    employees = Employee.objects.all().order_by("id")

    return render(
        request,
        "EMS/employee_list.html",
        {"employees": employees},
    )
