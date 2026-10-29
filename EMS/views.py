import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Employee


def employee_list(request):
    employees = Employee.objects.all().order_by("id")
    return render(
        request,
        "EMS/employee_list.html",
        {"employees": employees},
    )


@require_GET
def employee_api(request):
    employees = Employee.objects.all().order_by("id")

    data = [
        {
            "id": employee.id,
            "cen": employee.cen,
            "full_name": employee.full_name,
            "mobile": employee.mobile,
            "email": employee.email,
            "status": employee.status,
        }
        for employee in employees
    ]

    return JsonResponse({"employees": data})


@require_GET
def employee_detail_api(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return JsonResponse(
            {"error": "Employee not found"},
            status=404,
        )

    data = {
        "id": employee.id,
        "cen": employee.cen,
        "full_name": employee.full_name,
        "mobile": employee.mobile,
        "email": employee.email,
        "status": employee.status,
    }

    return JsonResponse(data)