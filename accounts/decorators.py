from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """Decorator that restricts view access to users with specified roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'User profile not found.')
                return redirect('accounts:login')
            if request.user.profile.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def field_access_required(view_func):
    """Decorator that ensures supervisors can only access their assigned field site data."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        profile = request.user.profile
        if profile.role == 'supervisor' and profile.field_site is None:
            messages.error(request, 'You are not assigned to any field site.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper
