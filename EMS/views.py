
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import Employee, EmployeeAddress
from .forms import EmployeeAddressForm


# =====================================================
# 1. EMPLOYEE LIST WITH SEARCH AND STATUS FILTER
# =====================================================

def employee_list(request):

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    employees = Employee.objects.all().order_by("id")

    # Search by CEN, employee name or mobile
    if search_query:
        employees = employees.filter(
            Q(cen__icontains=search_query)
            | Q(full_name__icontains=search_query)
            | Q(mobile__icontains=search_query)
        )

    # Filter by employee status
    valid_statuses = Employee.EmployeeStatus.values

    if status_filter in valid_statuses:
        employees = employees.filter(status=status_filter)
    else:
        status_filter = ""

    context = {
        "employees": employees,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": Employee.EmployeeStatus.choices,
    }

    return render(request, "EMS/employee_list.html", context)


# =====================================================
# 2. API - GET ALL EMPLOYEES
# =====================================================

@require_GET
def employee_api(request):

    employees = Employee.objects.all().order_by("id")

    data = []

    for employee in employees:
        data.append({
            "id": employee.id,
            "cen": employee.cen,
            "full_name": employee.full_name,
            "mobile": employee.mobile,
            "email": employee.email,
            "status": employee.status,
            "status_display": employee.get_status_display(),
        })

    return JsonResponse({"employees": data})


# =====================================================
# 3. API - GET SINGLE EMPLOYEE DETAILS
# =====================================================

@require_GET
def employee_detail_api(request, employee_id):

    employee = get_object_or_404(Employee, id=employee_id)

    # Do not expose Aadhaar, PAN or bank account numbers.
    data = {
        "id": employee.id,
        "cen": employee.cen,
        "society": employee.society,
        "full_name": employee.full_name,
        "date_of_birth": employee.date_of_birth.isoformat(),
        "gender": employee.get_gender_display(),
        "mobile": employee.mobile,
        "email": employee.email,
        "community": employee.community,
        "marital_status": employee.get_marital_status_display(),
        "status": employee.status,
        "status_display": employee.get_status_display(),
        "created_at": employee.created_at.isoformat(),
        "updated_at": employee.updated_at.isoformat(),
    }

    return JsonResponse(data)


# =====================================================
# 4. EMPLOYEE DETAILS PAGE
# =====================================================

@login_required
def employee_detail(request, employee_id):

    employee = get_object_or_404(
        Employee.objects.prefetch_related(
            "addresses",
            "qualifications",
            "family_members",
            "bank_accounts",
            "documents",
        ),
        id=employee_id,
    )

    # Mask Aadhaar number
    aadhaar = employee.aadhaar

    masked_aadhaar = (
        "*" * (len(aadhaar) - 4) + aadhaar[-4:]
        if aadhaar and len(aadhaar) > 4
        else "Not provided"
    )

    # Mask PAN number
    pan = employee.pan

    masked_pan = (
        "*" * (len(pan) - 3) + pan[-3:]
        if pan and len(pan) > 3
        else "Not provided"
    )

    # Prepare masked bank account details
    bank_accounts = []

    for account in employee.bank_accounts.all():

        account_number = account.account_number

        masked_account = (
            "*" * (len(account_number) - 4) + account_number[-4:]
            if len(account_number) > 4
            else "****"
        )

        bank_accounts.append({
            "account_holder_name": account.account_holder_name,
            "ifsc": account.ifsc,
            "masked_account_number": masked_account,
        })

    context = {
        "employee": employee,
        "masked_aadhaar": masked_aadhaar,
        "masked_pan": masked_pan,
        "addresses": employee.addresses.all(),
        "qualifications": employee.qualifications.all(),
        "family_members": employee.family_members.all(),
        "bank_accounts": bank_accounts,
        "documents": employee.documents.all(),
    }

    return render(
        request,
        "EMS/employee_detail.html",
        context,
    )


# =====================================================
# 5. ADD EMPLOYEE ADDRESS
# =====================================================

@login_required
def employee_address_add(request, employee_id):

    employee = get_object_or_404(Employee, id=employee_id)

    if request.method == "POST":

        form = EmployeeAddressForm(request.POST)

        if form.is_valid():

            address = form.save(commit=False)

            # Automatically connect address to selected employee
            address.employee = employee

            address.save()

            return redirect(
                "EMS:employee_detail",
                employee_id=employee.id,
            )

    else:

        form = EmployeeAddressForm()

    context = {
        "employee": employee,
        "form": form,
        "page_title": "Add Employee Address",
    }

    return render(
        request,
        "EMS/employee_address_form.html",
        context,
    )
