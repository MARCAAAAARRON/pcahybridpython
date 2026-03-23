from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from .models import UserProfile, FieldSite
from .decorators import role_required
from audit.models import AuditLog


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Audit log
            AuditLog.objects.create(
                user=user,
                action='login',
                details={'ip': request.META.get('REMOTE_ADDR')},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action='logout',
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# ── Super Admin: User Management ─────────────────────────────────────────────

@login_required
@role_required('sysadmin')
def user_list(request):
    """List all users (System Admin only)."""
    users = User.objects.select_related('profile', 'profile__field_site').all()
    field_sites = FieldSite.objects.all()
    return render(request, 'accounts/user_list.html', {
        'users': users,
        'field_sites': field_sites,
    })


@login_required
@role_required('sysadmin')
def user_create(request):
    """Create a new user (System Admin only)."""
    field_sites = FieldSite.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'supervisor')
        field_site_id = request.POST.get('field_site')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'accounts/user_form.html', {'field_sites': field_sites})

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        profile = user.profile
        profile.role = role
        if field_site_id:
            profile.field_site = FieldSite.objects.get(id=field_site_id)
        profile.save()

        AuditLog.objects.create(
            user=request.user,
            action='user_mgmt',
            model_name='User',
            object_id=user.id,
            details={'action': 'created', 'username': username, 'role': role},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, f'User "{username}" created successfully.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {'field_sites': field_sites})


@login_required
@role_required('sysadmin')
def user_edit(request, pk):
    """Edit a user (System Admin only)."""
    user_obj = get_object_or_404(User, pk=pk)
    field_sites = FieldSite.objects.all()

    if request.method == 'POST':
        user_obj.first_name = request.POST.get('first_name', '').strip()
        user_obj.last_name = request.POST.get('last_name', '').strip()
        user_obj.email = request.POST.get('email', '').strip()
        user_obj.is_active = request.POST.get('is_active') == 'on'
        user_obj.save()

        profile = user_obj.profile
        profile.role = request.POST.get('role', profile.role)
        field_site_id = request.POST.get('field_site')
        profile.field_site = FieldSite.objects.get(id=field_site_id) if field_site_id else None
        profile.save()

        # Reset password if provided
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            user_obj.set_password(new_password)
            user_obj.save()

        AuditLog.objects.create(
            user=request.user,
            action='user_mgmt',
            model_name='User',
            object_id=user_obj.id,
            details={'action': 'updated', 'username': user_obj.username},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, f'User "{user_obj.username}" updated.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'edit_user': user_obj,
        'field_sites': field_sites,
    })


@login_required
@role_required('sysadmin')
def user_toggle_active(request, pk):
    """Activate/deactivate a user (System Admin only)."""
    user_obj = get_object_or_404(User, pk=pk)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status = 'activated' if user_obj.is_active else 'deactivated'
    AuditLog.objects.create(
        user=request.user,
        action='user_mgmt',
        model_name='User',
        object_id=user_obj.id,
        details={'action': status, 'username': user_obj.username},
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    messages.success(request, f'User "{user_obj.username}" has been {status}.')
    return redirect('accounts:user_list')


@login_required
@role_required('sysadmin')
def update_user_role(request, pk):
    """AJAX endpoint to instantly change a user's role (System Admin only)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
        
    user_obj = get_object_or_404(User, pk=pk)
    new_role = request.POST.get('role')
    
    valid_roles = dict(UserProfile.ROLE_CHOICES).keys()
    if new_role not in valid_roles:
        return JsonResponse({'success': False, 'error': 'Invalid role.'}, status=400)
        
    if user_obj.profile.role == new_role:
        return JsonResponse({'success': True, 'message': 'Role unchanged.'})
        
    old_role_display = user_obj.profile.get_role_display()
    
    # Update role
    user_obj.profile.role = new_role
    user_obj.profile.save()
    
    new_role_display = user_obj.profile.get_role_display()
    
    # Audit trail
    AuditLog.objects.create(
        user=request.user,
        action='user_mgmt',
        model_name='UserProfile',
        object_id=user_obj.profile.id,
        details={'action': 'role_change', 'username': user_obj.username, 'from': old_role_display, 'to': new_role_display},
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'{user_obj.username} is now {new_role_display}',
        'new_role_display': new_role_display
    })


# ── Notifications ─────────────────────────────────────────────

@login_required
def mark_notification_read(request, pk):
    """Mark a specific notification as read."""
    from .models import Notification
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    if notification.link:
        return redirect(notification.link)
    
    # Redirect back to previous page
    next_url = request.META.get('HTTP_REFERER', 'dashboard:index')
    return redirect(next_url)


@login_required
def mark_all_notifications_read(request):
    """Mark all unread notifications as read."""
    from .models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Redirect back to previous page
    next_url = request.META.get('HTTP_REFERER', 'dashboard:index')
    return redirect(next_url)


@login_required
def notification_list(request):
    """Full page listing all notifications for the current user."""
    from .models import Notification
    all_notifications = Notification.objects.filter(user=request.user)
    unread_count = all_notifications.filter(is_read=False).count()
    return render(request, 'accounts/notification_list.html', {
        'all_notifications': all_notifications,
        'unread_count': unread_count,
    })


@login_required
def profile_view(request):
    """User profile page."""
    profile = request.user.profile
    
    if request.method == 'POST':
        # Update basic user info
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        
        # Change password if provided
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if new_password:
            if new_password == confirm_password:
                request.user.set_password(new_password)
                messages.success(request, 'Password changed successfully. Please log in again.')
            else:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'accounts/profile.html', {'profile': profile})
        
        signature_image = request.FILES.get('signature_image')
        if signature_image:
            profile.signature_image = signature_image
        
        profile.middle_initial = request.POST.get('middle_initial', '').strip()
        profile.save()
        
        request.user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html', {'profile': profile})

