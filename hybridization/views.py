from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import HybridizationRecord, RecordImage
from .forms import HybridizationRecordForm, RecordImageForm
from accounts.decorators import role_required, field_access_required
from accounts.models import Notification
from audit.models import AuditLog


def get_user_records(request):
    """Return queryset filtered by user's role and field site."""
    profile = request.user.profile
    if profile.role == 'supervisor':
        return HybridizationRecord.objects.filter(field_site=profile.field_site)
    elif profile.role in ('admin', 'superadmin'):
        return HybridizationRecord.objects.all()
    return HybridizationRecord.objects.none()


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def record_list(request):
    """List hybridization records — filtered by role."""
    records = get_user_records(request)

    # Filters
    status_filter = request.GET.get('status')
    search = request.GET.get('search', '').strip()

    if status_filter:
        records = records.filter(status=status_filter)
    if search:
        records = records.filter(
            hybrid_code__icontains=search
        ) | records.filter(
            crop_type__icontains=search
        )

    is_admin = request.user.profile.role in ('admin', 'superadmin')
    return render(request, 'hybridization/record_list.html', {
        'records': records,
        'status_filter': status_filter,
        'search': search,
        'is_admin': is_admin,
    })


@login_required
@role_required('supervisor', 'superadmin')
@field_access_required
def record_create(request):
    """Create a new hybridization record."""
    if request.method == 'POST':
        form = HybridizationRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.created_by = request.user
            record.field_site = request.user.profile.field_site
            record.save()

            # Handle image uploads
            for f in request.FILES.getlist('images'):
                RecordImage.objects.create(record=record, image=f)

            AuditLog.objects.create(
                user=request.user,
                action='create',
                model_name='HybridizationRecord',
                object_id=record.id,
                details={'hybrid_code': record.hybrid_code},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f'Record "{record.hybrid_code}" created successfully.')
            return redirect('hybridization:record_detail', pk=record.pk)
    else:
        form = HybridizationRecordForm()

    return render(request, 'hybridization/record_form.html', {
        'form': form,
        'is_create': True,
    })


@login_required
@role_required('supervisor', 'superadmin')
def record_update(request, pk):
    """Update an existing hybridization record (draft or revision only)."""
    record = get_object_or_404(HybridizationRecord, pk=pk, created_by=request.user)

    if record.status not in ('draft', 'returned'):
        messages.error(request, 'Only draft or returned records can be edited.')
        return redirect('hybridization:record_detail', pk=pk)

    if request.method == 'POST':
        form = HybridizationRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()

            for f in request.FILES.getlist('images'):
                RecordImage.objects.create(record=record, image=f)

            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='HybridizationRecord',
                object_id=record.id,
                details={'hybrid_code': record.hybrid_code},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Record updated successfully.')
            return redirect('hybridization:record_detail', pk=pk)
    else:
        form = HybridizationRecordForm(instance=record)

    return render(request, 'hybridization/record_form.html', {
        'form': form,
        'record': record,
        'is_create': False,
    })


@login_required
@role_required('supervisor', 'superadmin')
def record_submit(request, pk):
    """Submit a record for admin validation."""
    record = get_object_or_404(HybridizationRecord, pk=pk, created_by=request.user)

    if record.status not in ('draft', 'returned'):
        messages.error(request, 'Only draft or returned records can be submitted.')
        return redirect('hybridization:record_detail', pk=pk)

    from django.utils import timezone
    record.status = 'prepared'
    record.prepared_by = request.user
    record.date_prepared = timezone.now()
    record.save()

    AuditLog.objects.create(
        user=request.user,
        action='submit',
        model_name='HybridizationRecord',
        object_id=record.id,
        details={'hybrid_code': record.hybrid_code},
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # Notify the supervisor
    Notification.objects.create(
        user=request.user,
        message=f'Record "{record.hybrid_code}" submitted for validation.',
        link=f'/hybridization/{record.pk}/',
    )

    messages.success(request, f'Record "{record.hybrid_code}" submitted for validation.')
    return redirect('hybridization:record_detail', pk=pk)


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def record_detail(request, pk):
    """View full record details."""
    records = get_user_records(request)
    record = get_object_or_404(records, pk=pk)
    images = record.images.all()
    return render(request, 'hybridization/record_detail.html', {
        'record': record,
        'images': images,
    })


@login_required
@role_required('admin', 'superadmin')
def record_validate(request, pk):
    """Admin validates a submitted record."""
    record = get_object_or_404(HybridizationRecord, pk=pk)
    valid_status = record.status in ('prepared', 'reviewed')
    if not valid_status:
         return redirect('hybridization:record_detail', pk=pk)

    if request.method == 'POST':
        from django.utils import timezone
        action = request.POST.get('action')
        remarks = request.POST.get('admin_remarks', '').strip()

        if action == 'reviewed':
            record.status = 'reviewed'
            record.reviewed_by = request.user
            record.date_reviewed = timezone.now()
            record.admin_remarks = remarks
            record.save()
            audit_action = 'reviewed'
            msg = f'Record "{record.hybrid_code}" reviewed.'
        elif action == 'noted':
            record.status = 'noted'
            record.noted_by = request.user
            record.date_noted = timezone.now()
            record.admin_remarks = remarks
            record.save()
            audit_action = 'noted'
            msg = f'Record "{record.hybrid_code}" noted.'
        elif action == 'returned':
            record.status = 'returned'
            record.admin_remarks = remarks
            record.save()
            audit_action = 'returned'
            msg = f'Record "{record.hybrid_code}" returned to draft.'
        else:
            messages.error(request, 'Invalid action.')
            return redirect('hybridization:record_detail', pk=pk)

        AuditLog.objects.create(
            user=request.user,
            action=audit_action,
            model_name='HybridizationRecord',
            object_id=record.id,
            details={'hybrid_code': record.hybrid_code, 'remarks': remarks},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # Notify the supervisor who created the record
        Notification.objects.create(
            user=record.created_by,
            message=msg,
            link=f'/hybridization/{record.pk}/',
        )

        messages.success(request, msg)
        return redirect('hybridization:record_detail', pk=pk)

    return redirect('hybridization:record_detail', pk=pk)


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def record_delete(request, pk):
    """Delete a hybridization record. Supervisors: own draft/revision only; admins: any."""
    from django.urls import reverse

    record = get_object_or_404(HybridizationRecord, pk=pk)
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')

    if is_admin:
        can_delete = True
    else:
        can_delete = (
            record.created_by_id == request.user.id
            and record.status in ('draft', 'returned')
        )

    if not can_delete:
        messages.error(request, 'You do not have permission to delete this record.')
        return redirect('hybridization:record_list')

    if request.method == 'POST':
        hybrid_code = record.hybrid_code
        record.delete()
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            model_name='HybridizationRecord',
            object_id=pk,
            details={'hybrid_code': hybrid_code},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, f'Record "{hybrid_code}" deleted successfully.')
        return redirect('hybridization:record_list')

    return render(request, 'hybridization/confirm_delete.html', {
        'record': record,
        'cancel_url': reverse('hybridization:record_list'),
    })
