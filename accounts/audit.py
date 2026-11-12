
from accounts.models import AuditLog


def get_client_ip(request):
    # Use the direct connection address. Only trust forwarded
    # headers when your deployment has a trusted proxy configured.
    return request.META.get("REMOTE_ADDR")


def create_audit_log(request, action, instance, changes=None):
    actor = (
        request.user
        if request.user and request.user.is_authenticated
        else None
    )

    AuditLog.objects.create(
        actor=actor,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        changes=changes or {},
        ip_address=get_client_ip(request),
    )
