from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from .models import AuditLog


@login_required
@role_required('sysadmin')
def log_list(request):
    """View audit logs (System Admin only)."""
    logs = AuditLog.objects.select_related('user').all()

    # Filters
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)

    return render(request, 'audit/log_list.html', {
        'logs': logs[:100],
        'action_filter': action_filter,
        'user_filter': user_filter or '',
        'action_choices': AuditLog.ACTION_CHOICES,
    })
