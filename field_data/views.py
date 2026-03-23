from datetime import date, timedelta
import calendar
import json
import time

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import ExtractYear, ExtractMonth

from accounts.decorators import role_required
from accounts.models import FieldSite, Notification
from audit.models import AuditLog
from .models import (
    HybridDistribution,
    MonthlyHarvest,
    HarvestVariety,
    NurseryOperation,
    NurseryBatch,
    PollenProduction,
)
from .forms import (
    HybridDistributionForm,
    MonthlyHarvestForm,
    NurseryOperationForm,
    PollenProductionForm,
)
from .models import (
    FieldSite,
    HybridDistribution,
    MonthlyHarvest,
    NurseryOperation,
    PollenProduction,
    NurseryBatch,
    NurseryBatchVariety,
)
from .exports import EXPORTERS


MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


def _get_field_site_filter(request):
    """Return the field site for the current user (supervisor) or selected filter (admin)."""
    profile = request.user.profile
    if profile.role == 'supervisor':
        return profile.field_site
    site_id = request.GET.get('field_site')
    if site_id:
        try:
            return FieldSite.objects.get(pk=site_id)
        except FieldSite.DoesNotExist:
            pass
    return None


def _filter_by_site(qs, site):
    """Apply field site filter if a site is specified."""
    if site:
        return qs.filter(field_site=site)
    return qs


def _apply_date_filters(qs, request):
    """Apply year and month filters from GET params on report_month field."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year:
        try:
            qs = qs.filter(report_month__year=int(year))
        except (ValueError, TypeError):
            pass
    if month:
        try:
            qs = qs.filter(report_month__month=int(month))
        except (ValueError, TypeError):
            pass
    return qs


def _get_available_years(model):
    """Get distinct years from report_month across all records."""
    years = (
        model.objects
        .annotate(year=ExtractYear('report_month'))
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )
    return list(years)


def _date_filter_context(request, model):
    """Build the template context for date filter controls."""
    selected_year = request.GET.get('year', '')
    selected_month = request.GET.get('month', '')
    return {
        'available_years': _get_available_years(model),
        'selected_year': selected_year,
        'selected_month': selected_month,
        'months': [(i, MONTH_NAMES[i]) for i in range(1, 13)],
    }


def _notify_new_report(request, report_title, url_name_prefix, count=1, site=None):
    """Create notifications for Admin users when a new report is added."""
    # Target Senior Agriculturists (admin)
    admins = User.objects.filter(profile__role='admin').exclude(pk=request.user.pk)
    
    if site:
        site_name = site.name
        # Prioritize admins assigned to this site
        site_admins = list(admins.filter(profile__field_site=site))
        recipients = site_admins if site_admins else list(admins)
    elif hasattr(request.user, 'profile') and request.user.profile.field_site:
        site = request.user.profile.field_site
        site_name = site.name
        site_admins = list(admins.filter(profile__field_site=site))
        recipients = site_admins if site_admins else list(admins)
    else:
        site_name = 'Unknown Site'
        recipients = list(admins)
    
    if hasattr(request.user, 'profile') and request.user.profile.field_site:
        site_name = request.user.profile.field_site.name
    else:
        site_name = 'Unknown Site'
    
    uploader = request.user.get_full_name() or request.user.username
    
    if count > 1:
        message = f"[{site_name}] {uploader} submitted {count} new {report_title} records."
    else:
        message = f"[{site_name}] {uploader} submitted a new {report_title} record."
        
    try:
        link = reverse(f"field_data:{url_name_prefix}_list")
    except Exception:
        link = ""
        
    notifications = [
        Notification(user=user, message=message, link=link)
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def _notify_status_change(request, record, new_status, data_type):
    """Create targeted notifications for workflow status changes."""
    site_name = record.field_site.name if record.field_site else "Unknown Site"
    user_name = request.user.get_full_name() or request.user.username
    model_name = record._meta.verbose_name.title()
    
    recipients = []
    message = ""
    
    try:
        # Use terminal instead of nursery if it's a terminal report
        if data_type == 'nursery' and getattr(record, 'report_type', None) == 'terminal':
            link_name = "field_data:terminal_list"
        else:
            link_name = f"field_data:{data_type}_list"
        link = reverse(link_name)
    except Exception:
        link = ""

    if new_status == 'prepared':
        # Notify Senior Agriculturists (admin) assigned to site, or all admins if none assigned
        admins = User.objects.filter(profile__role='admin').exclude(pk=request.user.pk)
        if record.field_site:
            site_admins = list(admins.filter(profile__field_site=record.field_site))
            recipients = site_admins if site_admins else list(admins)
        else:
            recipients = list(admins)
        message = f"[{site_name}] {model_name} report prepared by {user_name}. Ready for review."

    elif new_status == 'reviewed':
        # Notify Chiefs (superadmin)
        chiefs = User.objects.filter(profile__role='superadmin').exclude(pk=request.user.pk)
        if record.field_site:
            site_chiefs = list(chiefs.filter(profile__field_site=record.field_site))
            recipients = site_chiefs if site_chiefs else list(chiefs)
        else:
            recipients = list(chiefs)
        message = f"[{site_name}] {model_name} report reviewed by {user_name}. Ready to be noted."

    elif new_status == 'noted':
        # Notify Preparer and Reviewer
        if record.prepared_by: recipients.append(record.prepared_by)
        if record.reviewed_by: recipients.append(record.reviewed_by)
        # Remove duplicates and current user
        recipients = list(set(recipients))
        if request.user in recipients: recipients.remove(request.user)
        message = f"[{site_name}] {model_name} report has been officially noted by {user_name}."

    elif new_status == 'returned_to_draft': # Note: current view resets to 'draft' but we can pass 'returned' logic
        # Notify Preparer (and Reviewer if it was noted)
        if record.prepared_by: recipients.append(record.prepared_by)
        if request.user in recipients: recipients.remove(request.user)
        message = f"[{site_name}] {model_name} report was returned to draft by {user_name}."

    if recipients and message:
        notification_objs = [
            Notification(user=user, message=message, link=link)
            for user in recipients
        ]
        Notification.objects.bulk_create(notification_objs)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def data_overview(request):
    """Overview page showing counts per data type."""
    site = _get_field_site_filter(request)
    is_admin = request.user.profile.role in ('admin', 'superadmin')

    # Apply date filters to counts too
    dist_qs = _apply_date_filters(_filter_by_site(HybridDistribution.objects.all(), site), request)
    harv_qs = _apply_date_filters(_filter_by_site(MonthlyHarvest.objects.all(), site), request)
    nurs_qs = _apply_date_filters(_filter_by_site(NurseryOperation.objects.filter(report_type='operation'), site), request)
    term_qs = _apply_date_filters(_filter_by_site(NurseryOperation.objects.filter(report_type='terminal'), site), request)
    poll_qs = _apply_date_filters(_filter_by_site(PollenProduction.objects.all(), site), request)

    # Collect all years across all models
    all_years = set()
    for model in [HybridDistribution, MonthlyHarvest, NurseryOperation, PollenProduction]:
        all_years.update(_get_available_years(model))
    all_years = sorted(all_years, reverse=True)

    selected_year = request.GET.get('year', '')
    selected_month = request.GET.get('month', '')

    ctx = {
        'distribution_count': dist_qs.count(),
        'harvest_count': harv_qs.count(),
        'nursery_count': nurs_qs.count(),
        'terminal_count': term_qs.count(),
        'pollen_count': poll_qs.count(),
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'selected_site': site,
        'is_admin': is_admin,
        'available_years': all_years,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'months': [(i, MONTH_NAMES[i]) for i in range(1, 13)],
    }
    return render(request, 'field_data/overview.html', ctx)


# ---------------------------------------------------------------------------
# List Views
# ---------------------------------------------------------------------------

def _list_view(request, model, template, extra_filter=None):
    """Generic list view with site + date filtering."""
    site = _get_field_site_filter(request)
    is_admin = request.user.profile.role in ('admin', 'superadmin')
    qs = model.objects.select_related('field_site')
    if extra_filter:
        qs = qs.filter(**extra_filter)
    records = _apply_date_filters(
        _filter_by_site(qs, site),
        request,
    )
    ctx = {
        'records': records[:500],
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'selected_site': site,
        'is_admin': is_admin,
    }
    ctx.update(_date_filter_context(request, model))
    return render(request, template, ctx)


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def distribution_list(request):
    """Custom list view to calculate and append totals."""
    site = _get_field_site_filter(request)
    is_admin = request.user.profile.role in ('admin', 'superadmin')
    
    qs = HybridDistribution.objects.select_related('field_site')
    records = _apply_date_filters(_filter_by_site(qs, site), request)
    
    # Calculate totals
    total_planted = 0
    total_received = 0
    for r in records:
        try:
            total_planted += int(r.seedlings_planted)
        except (ValueError, TypeError):
            pass
        try:
            val = str(r.seedlings_received).replace(',', '')
            total_received += int(val)
        except (ValueError, TypeError, AttributeError):
            pass
            
    ctx = {
        'records': records[:500],
        'total_planted': total_planted,
        'total_received': total_received if total_received > 0 else '',
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'selected_site': site,
        'is_admin': is_admin,
    }
    ctx.update(_date_filter_context(request, HybridDistribution))
    
    return render(request, 'field_data/distribution_list.html', ctx)


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def harvest_list(request):
    """List view with prefetched varieties."""
    site = _get_field_site_filter(request)
    is_admin = request.user.profile.role in ('admin', 'superadmin')
    qs = MonthlyHarvest.objects.select_related('field_site').prefetch_related('varieties')
    records = _apply_date_filters(_filter_by_site(qs, site), request)

    # region agent log: harvest_list snapshot for debug hypotheses H2-H4
    try:
        first = records.first()
        if first:
            varieties = list(
                first.varieties.values('variety', 'seednuts_type', 'seednuts_count')
            )[:3]
            log_entry = {
                "sessionId": "30a357",
                "runId": "pre-fix-harvest-list",
                "hypothesisId": "H2-H4",
                "location": "field_data/views.py:harvest_list",
                "message": "harvest_list first record snapshot",
                "data": {
                    "record_id": first.id,
                    "field_site": str(first.field_site),
                    "production_jan": first.production_jan,
                    "varieties": varieties,
                },
                "timestamp": int(time.time() * 1000),
            }
            with open(r"C:\Users\Marc Arron\PCA prototype\debug-30a357.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
    except Exception:
        # Logging must never break the view
        pass
    # endregion

    ctx = {
        'records': records[:500],
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'selected_site': site,
        'is_admin': is_admin,
    }
    ctx.update(_date_filter_context(request, MonthlyHarvest))
    return render(request, 'field_data/harvest_list.html', ctx)


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def nursery_list(request):
    return _list_view(request, NurseryOperation, 'field_data/nursery_list.html',
                      extra_filter={'report_type': 'operation'})


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def terminal_list(request):
    return _list_view(request, NurseryOperation, 'field_data/terminal_list.html',
                      extra_filter={'report_type': 'terminal'})


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def pollen_list(request):
    return _list_view(request, PollenProduction, 'field_data/pollen_list.html')


# ---------------------------------------------------------------------------
# Create Views (Manual Data Entry)
# ---------------------------------------------------------------------------

def _handle_create(request, FormClass, model_name, redirect_url, template, initial=None):
    """Generic create handler for field data records."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            record = form.save(commit=False)

            # Apply initial values (e.g., report_type)
            if initial:
                for k, v in initial.items():
                    setattr(record, k, v)

            # Assign field site
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    record.field_site = FieldSite.objects.get(pk=site_id)
                else:
                    messages.error(request, 'Please select a field site.')
                    return render(request, template, {
                        'form': form,
                        'is_admin': is_admin,
                        'field_sites': FieldSite.objects.all(),
                    })
            else:
                record.field_site = profile.field_site

            record.save()

            AuditLog.objects.create(
                user=request.user,
                action='create',
                model_name=model_name,
                object_id=record.id,
                details={'type': model_name},
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            if model_name == 'PollenProduction':
                _notify_new_report(request, 'Pollen', 'pollen', site=record.field_site)
            else:
                _notify_new_report(request, model_name, model_name.lower(), site=record.field_site)

            messages.success(request, f'{model_name} record added successfully.')
            return redirect(redirect_url)
    else:
        form = FormClass()

    return render(request, template, {
        'form': form,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def distribution_create(request):
    """Custom create handler to save multiple HybridDistribution records at once."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    template = 'field_data/distribution_form.html'

    if request.method == 'POST':
        # Use the raw POST data instead of form validation as we're handling arrays
        report_month = request.POST.get('report_month')
        if not report_month:
            messages.error(request, 'Please select a report month.')
            return render(request, template, {
                'form': HybridDistributionForm(request.POST),
                'is_admin': is_admin,
                'field_sites': FieldSite.objects.all(),
            })

        # Determine field site
        if is_admin:
            site_id = request.POST.get('field_site')
            if not site_id:
                messages.error(request, 'Please select a field site.')
                return render(request, template, {
                    'form': HybridDistributionForm(request.POST),
                    'is_admin': is_admin,
                    'field_sites': FieldSite.objects.all(),
                })
            field_site = FieldSite.objects.get(pk=site_id)
        else:
            field_site = profile.field_site

        # Get arrays of farmer data from POST
        regions = request.POST.getlist('dist_region[]')
        provinces = request.POST.getlist('dist_province[]')
        districts = request.POST.getlist('dist_district[]')
        
        municipalities = request.POST.getlist('dist_municipality[]')
        barangays = request.POST.getlist('dist_barangay[]')
        last_names = request.POST.getlist('dist_last_name[]')
        first_names = request.POST.getlist('dist_first_name[]')
        mis = request.POST.getlist('dist_mi[]')
        genders = request.POST.getlist('dist_gender[]')
        
        farm_barangays = request.POST.getlist('dist_farm_barangay[]')
        farm_municipalities = request.POST.getlist('dist_farm_municipality[]')
        
        received_counts = request.POST.getlist('dist_received[]')
        date_received = request.POST.getlist('dist_date_received[]')
        varieties = request.POST.getlist('dist_variety[]')
        planted_counts = request.POST.getlist('dist_planted[]')
        date_planted = request.POST.getlist('dist_date_planted[]')
        remarks_list = request.POST.getlist('dist_remarks[]')

        created_count = 0
        for i in range(len(last_names)):
            # Skip if last name is empty
            if not last_names[i].strip():
                continue

            gender = genders[i] if i < len(genders) else ''
            
            # Parse dates (allow empty)
            d_received = date_received[i] if i < len(date_received) and date_received[i] else None
            d_planted = date_planted[i] if i < len(date_planted) and date_planted[i] else None
            
            # Parse text value for seedlings received (e.g. "Owner" or "100")
            r_val = received_counts[i].strip() if i < len(received_counts) and received_counts[i] else ''
                
            # Parse integer for planted count
            try:
                p_count = int(planted_counts[i]) if i < len(planted_counts) and planted_counts[i] else 0
            except ValueError:
                p_count = 0

            record = HybridDistribution.objects.create(
                field_site=field_site,
                report_month=report_month,
                
                region=regions[i].strip() if i < len(regions) else 'VII',
                province=provinces[i].strip() if i < len(provinces) else 'BOHOL',
                district=districts[i].strip() if i < len(districts) else '',
                
                municipality=municipalities[i].strip() if i < len(municipalities) else '',
                barangay=barangays[i].strip() if i < len(barangays) else '',
                farmer_last_name=last_names[i].strip(),
                farmer_first_name=first_names[i].strip() if i < len(first_names) else '',
                farmer_middle_initial=mis[i].strip() if i < len(mis) else '',
                is_male=(gender == 'M'),
                is_female=(gender == 'F'),
                
                farm_barangay=farm_barangays[i].strip() if i < len(farm_barangays) else '',
                farm_municipality=farm_municipalities[i].strip() if i < len(farm_municipalities) else '',
                farm_province=provinces[i].strip() if i < len(provinces) else 'BOHOL',
                
                seedlings_received=r_val,
                date_received=d_received,
                variety=varieties[i].strip() if i < len(varieties) else '',
                seedlings_planted=p_count,
                date_planted=d_planted,
                remarks=remarks_list[i].strip() if i < len(remarks_list) else '',
            )
            created_count += 1
            
            AuditLog.objects.create(
                user=request.user, action='create',
                model_name='HybridDistribution', object_id=record.id,
                details={'type': 'HybridDistribution', 'farmer': record.farmer_last_name},
                ip_address=request.META.get('REMOTE_ADDR'),
            )

        if created_count > 0:
            _notify_new_report(request, 'Distribution', 'distribution', count=created_count, site=field_site)
            messages.success(request, f'Successfully saved {created_count} distribution record(s).')
            return redirect('field_data:distribution_list')
        else:
            messages.warning(request, 'No valid farmer records were provided.')
                
            return redirect('field_data:distribution_list')
    else:
        # Initialize form with defaults
        form = HybridDistributionForm(initial={'region': 'VII', 'province': 'BOHOL', 'farm_province': 'BOHOL'})

    return render(request, template, {
        'form': form,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def harvest_create(request):
    """Custom create handler to also save HarvestVariety child records."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    template = 'field_data/harvest_form.html'

    if request.method == 'POST':
        form = MonthlyHarvestForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)

            # Assign field site
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    record.field_site = FieldSite.objects.get(pk=site_id)
                else:
                    messages.error(request, 'Please select a field site.')
                    return render(request, template, {
                        'form': form,
                        'is_admin': is_admin,
                        'field_sites': FieldSite.objects.all(),
                    })
            else:
                record.field_site = profile.field_site

            record.save()

            # Save variety child records
            varieties = request.POST.getlist('var_variety[]')
            types = request.POST.getlist('var_type[]')
            counts = request.POST.getlist('var_count[]')
            remarks = request.POST.getlist('var_remarks[]')
            # Handle potential mismatch in list lengths if a field was missing
            for i in range(len(varieties)):
                v = varieties[i].strip() if i < len(varieties) else ''
                t = types[i].strip() if i < len(types) else ''
                c = counts[i] if i < len(counts) else 0
                r = remarks[i].strip() if i < len(remarks) else ''
                if v:  # skip empty rows
                    HarvestVariety.objects.create(
                        harvest=record,
                        variety=v,
                        seednuts_type=t,
                        seednuts_count=int(c) if c else 0,
                        remarks=r
                    )

            AuditLog.objects.create(
                user=request.user, action='create',
                model_name='MonthlyHarvest', object_id=record.id,
                details={'type': 'MonthlyHarvest'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            _notify_new_report(request, 'Harvest', 'harvest', site=record.field_site)
            messages.success(request, 'Harvest record added successfully.')
            return redirect('field_data:harvest_list')
    else:
        form = MonthlyHarvestForm()

    return render(request, template, {
        'form': form,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def _handle_nursery_create(request, initial, list_url, template):
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    
    if request.method == 'POST':
        form = NurseryOperationForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    record.field_site = FieldSite.objects.get(pk=site_id)
                else:
                    messages.error(request, 'Please select a field site.')
                    return render(request, template, {
                        'form': form,
                        'is_admin': is_admin,
                        'field_sites': FieldSite.objects.all(),
                    })
            else:
                record.field_site = profile.field_site

            record.save()
            
            # Save batch and variety child records
            batch_indices = request.POST.getlist('batch_index[]')
            
            for b_idx_str in batch_indices:
                try:
                    b_inc = int(b_idx_str)
                except ValueError:
                    continue

                # Batch level fields
                b_harvesteds = request.POST.getlist(f'batch_harvested_{b_inc}[]')
                b_d_harvesteds = request.POST.getlist(f'batch_d_harvested_{b_inc}[]')
                b_d_receiveds = request.POST.getlist(f'batch_d_received_{b_inc}[]')
                b_sources = request.POST.getlist(f'batch_source_{b_inc}[]')

                def safe_int_b(arr):
                    try:
                        return int(arr[0]) if arr and arr[0] else 0
                    except ValueError:
                        return 0
                
                def safe_str_b(arr):
                    return arr[0].strip() if arr else ''

                batch = NurseryBatch.objects.create(
                    nursery=record,
                    seednuts_harvested=safe_int_b(b_harvesteds),
                    date_harvested=safe_str_b(b_d_harvesteds),
                    date_received=safe_str_b(b_d_receiveds),
                    source_of_seednuts=safe_str_b(b_sources),
                )

                # Variety level fields for this batch
                varieties = request.POST.getlist(f'variety_{b_inc}[]')
                sowns = request.POST.getlist(f'sown_{b_inc}[]')
                d_sowns = request.POST.getlist(f'd_sown_{b_inc}[]')
                germinateds = request.POST.getlist(f'germinated_{b_inc}[]')
                ungerminateds = request.POST.getlist(f'ungerminated_{b_inc}[]')
                culleds = request.POST.getlist(f'culled_{b_inc}[]')
                goods = request.POST.getlist(f'good_{b_inc}[]')
                readys = request.POST.getlist(f'ready_{b_inc}[]')
                dispatcheds = request.POST.getlist(f'dispatched_{b_inc}[]')
                remarks = request.POST.getlist(f'remarks_{b_inc}[]')

                for i in range(len(varieties)):
                    v = varieties[i].strip() if i < len(varieties) else ''
                    if v:
                        def safe_int(idx, arr):
                            try:
                                return int(arr[idx]) if idx < len(arr) and arr[idx] else 0
                            except ValueError:
                                return 0
                        def safe_str(idx, arr):
                            return arr[idx].strip() if idx < len(arr) else ''
                        
                        NurseryBatchVariety.objects.create(
                            batch=batch,
                            variety=v,
                            seednuts_sown=safe_int(i, sowns),
                            date_sown=safe_str(i, d_sowns),
                            seedlings_germinated=safe_int(i, germinateds),
                            ungerminated_seednuts=safe_int(i, ungerminateds),
                            culled_seedlings=safe_int(i, culleds),
                            good_seedlings=safe_int(i, goods),
                            ready_to_plant=safe_int(i, readys),
                            seedlings_dispatched=safe_int(i, dispatcheds),
                            remarks=safe_str(i, remarks),
                        )

            AuditLog.objects.create(
                user=request.user, action='create',
                model_name='NurseryOperation', object_id=record.id,
                details={'type': 'NurseryOperation'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            if initial and initial.get('report_type') == 'terminal':
                _notify_new_report(request, 'Terminal Report', 'terminal', site=record.field_site)
            else:
                _notify_new_report(request, 'Nursery', 'nursery', site=record.field_site)
                
            messages.success(request, 'Nursery record added successfully.')
            return redirect(list_url)
    else:
        form = NurseryOperationForm(initial=initial)

    return render(request, template, {
        'form': form,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def nursery_create(request):
    return _handle_nursery_create(
        request, {'report_type': 'operation'},
        'field_data:nursery_list', 'field_data/nursery_form.html'
    )


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def terminal_create(request):
    return _handle_nursery_create(
        request, {'report_type': 'terminal'},
        'field_data:terminal_list', 'field_data/terminal_form.html'
    )


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def pollen_create(request):
    return _handle_create(
        request, PollenProductionForm, 'PollenProduction',
        'field_data:pollen_list', 'field_data/pollen_form.html',
    )


# ---------------------------------------------------------------------------
# Update (Edit) Views
# ---------------------------------------------------------------------------

def _get_editable_record(model, pk, request, extra_filter=None):
    """Return record for editing or None; supervisors limited to their field_site."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    qs = model.objects.filter(pk=pk)
    if extra_filter:
        qs = qs.filter(**extra_filter)
    if not is_admin:
        qs = qs.filter(field_site=profile.field_site)
    try:
        return qs.get()
    except model.DoesNotExist:
        return None


def _handle_update(request, pk, FormClass, model, model_name, list_url_name, template, extra_filter=None):
    """Generic update handler for field data records."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    record = _get_editable_record(model, pk, request, extra_filter=extra_filter)
    if not record:
        messages.error(request, 'Record not found or you do not have permission to edit it.')
        return redirect(list_url_name)

    if request.method == 'POST':
        form = FormClass(request.POST, instance=record)
        if form.is_valid():
            obj = form.save(commit=False)
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    obj.field_site = FieldSite.objects.get(pk=site_id)
            # else keep existing field_site
            obj.save()
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name=model_name,
                object_id=obj.pk,
                details={'type': model_name},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f'{model_name} record updated successfully.')
            return redirect(list_url_name)
    else:
        form = FormClass(instance=record)

    return render(request, template, {
        'form': form,
        'record': record,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'is_edit': True,
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def distribution_update(request, pk):
    return _handle_update(
        request, pk, HybridDistributionForm, HybridDistribution, 'HybridDistribution',
        'field_data:distribution_list', 'field_data/distribution_form.html',
    )


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def harvest_update(request, pk):
    """Update harvest record and its variety child records."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    record = _get_editable_record(MonthlyHarvest, pk, request)
    if not record:
        messages.error(request, 'Record not found or you do not have permission to edit it.')
        return redirect('field_data:harvest_list')

    template = 'field_data/harvest_form.html'

    if request.method == 'POST':
        form = MonthlyHarvestForm(request.POST, instance=record)
        if form.is_valid():
            obj = form.save(commit=False)
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    obj.field_site = FieldSite.objects.get(pk=site_id)
            obj.save()
            # Replace variety rows: delete existing, create from POST
            record.varieties.all().delete()
            varieties = request.POST.getlist('var_variety[]')
            types = request.POST.getlist('var_type[]')
            counts = request.POST.getlist('var_count[]')
            remarks = request.POST.getlist('var_remarks[]')
            for i in range(len(varieties)):
                v = varieties[i].strip() if i < len(varieties) else ''
                t = types[i].strip() if i < len(types) else ''
                c = counts[i] if i < len(counts) else 0
                r = remarks[i].strip() if i < len(remarks) else ''
                if v:
                    HarvestVariety.objects.create(
                        harvest=record,
                        variety=v,
                        seednuts_type=t,
                        seednuts_count=int(c) if c else 0,
                        remarks=r
                    )
            AuditLog.objects.create(
                user=request.user, action='update',
                model_name='MonthlyHarvest', object_id=record.pk,
                details={'type': 'MonthlyHarvest'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Harvest record updated successfully.')
            return redirect('field_data:harvest_list')
    else:
        form = MonthlyHarvestForm(instance=record)

    existing_varieties = list(record.varieties.values_list('variety', 'seednuts_type', 'seednuts_count', 'remarks'))

    return render(request, template, {
        'form': form,
        'record': record,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'is_edit': True,
        'existing_varieties': existing_varieties,
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def _handle_nursery_update(request, pk, list_url, template, extra_filter=None):
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    record = _get_editable_record(NurseryOperation, pk, request, extra_filter=extra_filter)
    if not record:
        messages.error(request, 'Record not found or you do not have permission to edit it.')
        return redirect(list_url)

    if request.method == 'POST':
        form = NurseryOperationForm(request.POST, instance=record)
        if form.is_valid():
            obj = form.save(commit=False)
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    obj.field_site = FieldSite.objects.get(pk=site_id)
            obj.save()
            
            # Recreate batches
            record.batches.all().delete()
            
            batch_indices = request.POST.getlist('batch_index[]')
            
            for b_idx_str in batch_indices:
                try:
                    b_inc = int(b_idx_str)
                except ValueError:
                    continue

                # Batch level fields
                b_harvesteds = request.POST.getlist(f'batch_harvested_{b_inc}[]')
                b_d_harvesteds = request.POST.getlist(f'batch_d_harvested_{b_inc}[]')
                b_d_receiveds = request.POST.getlist(f'batch_d_received_{b_inc}[]')
                b_sources = request.POST.getlist(f'batch_source_{b_inc}[]')

                def safe_int_b(arr):
                    try:
                        return int(arr[0]) if arr and arr[0] else 0
                    except ValueError:
                        return 0
                
                def safe_str_b(arr):
                    return arr[0].strip() if arr else ''

                batch = NurseryBatch.objects.create(
                    nursery=record,
                    seednuts_harvested=safe_int_b(b_harvesteds),
                    date_harvested=safe_str_b(b_d_harvesteds),
                    date_received=safe_str_b(b_d_receiveds),
                    source_of_seednuts=safe_str_b(b_sources),
                )

                # Variety level fields for this batch
                varieties = request.POST.getlist(f'variety_{b_inc}[]')
                sowns = request.POST.getlist(f'sown_{b_inc}[]')
                d_sowns = request.POST.getlist(f'd_sown_{b_inc}[]')
                germinateds = request.POST.getlist(f'germinated_{b_inc}[]')
                ungerminateds = request.POST.getlist(f'ungerminated_{b_inc}[]')
                culleds = request.POST.getlist(f'culled_{b_inc}[]')
                goods = request.POST.getlist(f'good_{b_inc}[]')
                readys = request.POST.getlist(f'ready_{b_inc}[]')
                dispatcheds = request.POST.getlist(f'dispatched_{b_inc}[]')
                remarks = request.POST.getlist(f'remarks_{b_inc}[]')

                for i in range(len(varieties)):
                    v = varieties[i].strip() if i < len(varieties) else ''
                    if v:
                        def safe_int(idx, arr):
                            try:
                                return int(arr[idx]) if idx < len(arr) and arr[idx] else 0
                            except ValueError:
                                return 0
                        def safe_str(idx, arr):
                            return arr[idx].strip() if idx < len(arr) else ''
                        
                        NurseryBatchVariety.objects.create(
                            batch=batch,
                            variety=v,
                            seednuts_sown=safe_int(i, sowns),
                            date_sown=safe_str(i, d_sowns),
                            seedlings_germinated=safe_int(i, germinateds),
                            ungerminated_seednuts=safe_int(i, ungerminateds),
                            culled_seedlings=safe_int(i, culleds),
                            good_seedlings=safe_int(i, goods),
                            ready_to_plant=safe_int(i, readys),
                            seedlings_dispatched=safe_int(i, dispatcheds),
                            remarks=safe_str(i, remarks),
                        )

            AuditLog.objects.create(
                user=request.user, action='update',
                model_name='NurseryOperation', object_id=record.pk,
                details={'type': 'NurseryOperation'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Nursery record updated successfully.')
            return redirect(list_url)
    else:
        form = NurseryOperationForm(instance=record)

    existing_batches = list(record.batches.values(
        'variety', 'seednuts_harvested', 'date_harvested', 'date_received', 
        'source_of_seednuts', 'seednuts_sown', 'date_sown', 'seedlings_germinated', 
        'ungerminated_seednuts', 'culled_seedlings', 'good_seedlings', 
        'ready_to_plant', 'seedlings_dispatched', 'remarks'
    ))

    return render(request, template, {
        'form': form,
        'record': record,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'is_edit': True,
        'existing_batches': existing_batches,
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def nursery_update(request, pk):
    return _handle_nursery_update(
        request, pk, 'field_data:nursery_list', 'field_data/nursery_form.html',
        extra_filter={'report_type': 'operation'}
    )


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def terminal_update(request, pk):
    return _handle_nursery_update(
        request, pk, 'field_data:terminal_list', 'field_data/terminal_form.html',
        extra_filter={'report_type': 'terminal'}
    )


import re

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def pollen_update(request, pk):
    # Retrieve record and strip any textual data from number fields so they display in NumberInput
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    record = _get_editable_record(PollenProduction, pk, request)
    if not record:
        messages.error(request, 'Record not found or you do not have permission to edit it.')
        return redirect('field_data:pollen_list')

    # Strip text out from char fields that are treated as numbers
    number_fields = ['ending_balance_prev', 'pollens_received', 'week1', 'week2', 'week3', 'week4', 'week5', 'total_utilization', 'ending_balance']
    for field in number_fields:
        val = getattr(record, field)
        if val:
            try:
                # keep numbers, dot, and minus
                cleaned = re.sub(r'[^\d.-]', '', str(val))
                setattr(record, field, cleaned)
            except Exception:
                pass

    if request.method == 'POST':
        form = PollenProductionForm(request.POST, instance=record)
        if form.is_valid():
            obj = form.save(commit=False)
            if is_admin:
                site_id = request.POST.get('field_site')
                if site_id:
                    obj.field_site = FieldSite.objects.get(pk=site_id)
            obj.save()
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='PollenProduction',
                object_id=obj.pk,
                details={'type': 'PollenProduction'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'PollenProduction record updated successfully.')
            return redirect('field_data:pollen_list')
    else:
        form = PollenProductionForm(instance=record)

    return render(request, 'field_data/pollen_form.html', {
        'form': form,
        'record': record,
        'is_admin': is_admin,
        'field_sites': FieldSite.objects.all() if is_admin else [],
        'is_edit': True,
    })


# ---------------------------------------------------------------------------
# Carry-Forward: Fetch previous harvest data for a new record
# ---------------------------------------------------------------------------

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def harvest_carry_forward(request):
    """Return the most recent harvest record data as JSON for carry-forward."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')

    # Determine field site
    if is_admin:
        site_id = request.GET.get('field_site')
        if not site_id:
            return JsonResponse({'found': False})
        try:
            site = FieldSite.objects.get(pk=site_id)
        except FieldSite.DoesNotExist:
            return JsonResponse({'found': False})
    else:
        site = profile.field_site

    if not site:
        return JsonResponse({'found': False})

    # Find the most recent harvest record for this site
    latest = (
        MonthlyHarvest.objects
        .filter(field_site=site)
        .prefetch_related('varieties')
        .order_by('-report_month')
        .first()
    )
    if not latest:
        return JsonResponse({'found': False})

    varieties = [
        {
            'variety': v.variety,
            'seednuts_type': v.seednuts_type,
        }
        for v in latest.varieties.all()
    ]
    
    next_month_date = ""
    if latest.report_month:
        y = latest.report_month.year
        m = latest.report_month.month
        if m == 12:
            next_m = 1
            next_y = y + 1
        else:
            next_m = m + 1
            next_y = y
        next_month_date = f"{next_y:04d}-{next_m:02d}-01"

    return JsonResponse({
        'found': True,
        'location': latest.location or '',
        'farm_name': latest.farm_name or '',
        'area_ha': latest.area_ha or '',
        'age_of_palms': latest.age_of_palms or '',
        'num_hybridized_palms': latest.num_hybridized_palms or 0,
        'varieties': varieties,
        'next_month_date': next_month_date,
    })

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def pollen_carry_forward(request):
    """Return the most recent pollen record data as JSON for carry-forward."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')

    # Determine field site
    if is_admin:
        site_id = request.GET.get('field_site')
        if not site_id:
            return JsonResponse({'found': False})
        try:
            site = FieldSite.objects.get(pk=site_id)
        except FieldSite.DoesNotExist:
            return JsonResponse({'found': False})
    else:
        site = profile.field_site

    if not site:
        return JsonResponse({'found': False})

    # Find the most recent pollen record for this site
    latest = (
        PollenProduction.objects
        .filter(field_site=site)
        .order_by('-report_month')
        .first()
    )
    if not latest:
        return JsonResponse({'found': False})

    next_month_date = ""
    next_month_label = ""
    if latest.report_month:
        y = latest.report_month.year
        m = latest.report_month.month
        if m == 12:
            next_m = 1
            next_y = y + 1
        else:
            next_m = m + 1
            next_y = y
        next_month_date = f"{next_y:04d}-{next_m:02d}-01"
        try:
            SHORT_MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            next_month_label = SHORT_MONTHS[next_m]
        except IndexError:
            pass

    import re
    ending_balance_cleaned = ''
    if latest.ending_balance:
        ending_balance_cleaned = re.sub(r'[^\d.-]', '', str(latest.ending_balance))

    return JsonResponse({
        'found': True,
        'pollen_variety': latest.pollen_variety or '',
        'ending_balance': ending_balance_cleaned,
        'next_month_date': next_month_date,
        'next_month_label': next_month_label,
    })


def _get_carry_forward_site(request):
    """Helper: resolve field site for carry-forward requests."""
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    if is_admin:
        site_id = request.GET.get('field_site')
        if not site_id:
            return None
        try:
            return FieldSite.objects.get(pk=site_id)
        except FieldSite.DoesNotExist:
            return None
    return profile.field_site


def _nursery_batches_to_json(nursery_record):
    """Serialize NurseryBatch and NurseryBatchVariety rows to a hierarchical list of dicts."""
    batches = []
    for b in nursery_record.batches.prefetch_related('varieties').all():
        varieties = []
        for v in b.varieties.all():
            varieties.append({
                'variety': v.variety or '',
                'seednuts_sown': v.seednuts_sown or 0,
                'date_sown': v.date_sown or '',
                'seedlings_germinated': v.seedlings_germinated or 0,
                'ungerminated_seednuts': v.ungerminated_seednuts or 0,
                'culled_seedlings': v.culled_seedlings or 0,
                'good_seedlings': v.good_seedlings or 0,
                'ready_to_plant': v.ready_to_plant or 0,
                'seedlings_dispatched': v.seedlings_dispatched or 0,
                'remarks': v.remarks or '',
            })
        
        batches.append({
            'source_of_seednuts': b.source_of_seednuts or '',
            'date_received': b.date_received or '',
            'seednuts_harvested': b.seednuts_harvested or 0,
            'date_harvested': b.date_harvested or '',
            'varieties': varieties,
        })
    return batches


def _next_month_date(report_month):
    """Compute the next month date string from a report_month."""
    if not report_month:
        return ''
    y, m = report_month.year, report_month.month
    if m == 12:
        return f"{y + 1:04d}-01-01"
    return f"{y:04d}-{m + 1:02d}-01"


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def nursery_carry_forward(request):
    """Return the most recent nursery operation data as JSON for carry-forward."""
    site = _get_carry_forward_site(request)
    if not site:
        return JsonResponse({'found': False})

    latest = (
        NurseryOperation.objects
        .filter(field_site=site, report_type='operation')
        .prefetch_related('batches')
        .order_by('-report_month')
        .first()
    )
    if not latest:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'next_month_date': _next_month_date(latest.report_month),
        # Constant fields
        'region_province_district': latest.region_province_district or '',
        'barangay_municipality': latest.barangay_municipality or '',
        'proponent_entity': latest.proponent_entity or '',
        'proponent_representative': latest.proponent_representative or '',
        'target_seednuts': latest.target_seednuts or 0,
        # Batch data
        'batches': _nursery_batches_to_json(latest),
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def terminal_carry_forward(request):
    """Return the most recent nursery operation data as JSON for terminal report carry-forward."""
    site = _get_carry_forward_site(request)
    if not site:
        return JsonResponse({'found': False})

    latest = (
        NurseryOperation.objects
        .filter(field_site=site, report_type='operation')
        .prefetch_related('batches')
        .order_by('-report_month')
        .first()
    )
    if not latest:
        return JsonResponse({'found': False})

    # Derive nursery_start_date from the earliest date_sown across all varieties in all batches
    nursery_start = ''
    from datetime import datetime as dt
    for b in latest.batches.prefetch_related('varieties').all():
        for v in b.varieties.all():
            if v.date_sown:
                try:
                    parsed = dt.strptime(v.date_sown.strip(), '%B %d, %Y')
                    iso = parsed.strftime('%Y-%m-%d')
                    if not nursery_start or iso < nursery_start:
                        nursery_start = iso
                except ValueError:
                    # Try shorter format (e.g. "Sept 11, 2025")
                    try:
                        parsed = dt.strptime(v.date_sown.strip(), '%b %d, %Y')
                        iso = parsed.strftime('%Y-%m-%d')
                        if not nursery_start or iso < nursery_start:
                            nursery_start = iso
                    except ValueError:
                        pass

    return JsonResponse({
        'found': True,
        'next_month_date': _next_month_date(latest.report_month),
        # Constant fields
        'region_province_district': latest.region_province_district or '',
        'barangay_municipality': latest.barangay_municipality or '',
        'proponent_entity': latest.proponent_entity or '',
        'proponent_representative': latest.proponent_representative or '',
        'target_seednuts': latest.target_seednuts or 0,
        # Terminal-specific
        'nursery_start_date': nursery_start,
        # Batch data
        'batches': _nursery_batches_to_json(latest),
    })


# ---------------------------------------------------------------------------
# Excel Export / Download
# ---------------------------------------------------------------------------

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def export_excel(request, data_type):
    """Download field data as an Excel file."""
    site = _get_field_site_filter(request)

    MODEL_MAP = {
        'distribution': HybridDistribution,
        'harvest': MonthlyHarvest,
        'nursery': NurseryOperation,
        'terminal': NurseryOperation,
        'pollen': PollenProduction,
    }

    LABEL_MAP = {
        'distribution': 'Hybrid_Distribution',
        'harvest': 'Monthly_Harvest',
        'nursery': 'Nursery_Operations',
        'terminal': 'Terminal_Report',
        'pollen': 'Pollen_Production',
    }

    # Extra queryset filters for report_type
    EXTRA_FILTER = {
        'nursery': {'report_type': 'operation'},
        'terminal': {'report_type': 'terminal'},
    }

    model = MODEL_MAP.get(data_type)
    exporter = EXPORTERS.get(data_type)
    label = LABEL_MAP.get(data_type, data_type)

    if not model or not exporter:
        messages.error(request, 'Invalid data type.')
        return redirect('field_data:overview')

    qs = model.objects.select_related('field_site').all()
    extra = EXTRA_FILTER.get(data_type)
    if extra:
        qs = qs.filter(**extra)
    qs = _apply_date_filters(
        _filter_by_site(qs, site),
        request,
    )
    site_name = site.name if site else 'All_Sites'

    if not qs.exists():
        messages.warning(request, f'No data available for {label.replace("_", " ")} with the selected filters.')
        referer = request.META.get('HTTP_REFERER')
        return redirect(referer if referer else 'field_data:overview')

    # Build filename with date suffix
    year = request.GET.get('year', '')
    month = request.GET.get('month', '')
    date_suffix = ''
    if year:
        date_suffix += f'_{year}'
    if month:
        try:
            date_suffix += f'_{MONTH_NAMES[int(month)]}'
        except (ValueError, IndexError):
            pass

    filename = f'{label}_{site_name.replace(" ", "_")}{date_suffix}.xlsx'

    # Compute as_of_date from year/month filters
    as_of_date = None
    if year and month:
        try:
            y, m = int(year), int(month)
            last_day = calendar.monthrange(y, m)[1]
            as_of_date = date(y, m, last_day)
        except (ValueError, TypeError):
            pass
    elif year:
        try:
            as_of_date = date(int(year), 12, 31)
        except (ValueError, TypeError):
            pass

    buf = exporter(qs, site_name.replace('_', ' '), as_of_date=as_of_date)

    AuditLog.objects.create(
        user=request.user,
        action='export',
        model_name=label,
        object_id=0,
        details={
            'type': data_type,
            'field_site': site_name,
            'count': qs.count(),
            'year': year,
            'month': month,
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Record Deletion
# ---------------------------------------------------------------------------

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def record_delete(request, data_type, pk):
    """Unified delete view for all field data records."""
    MODEL_MAP = {
        'distribution': HybridDistribution,
        'harvest': MonthlyHarvest,
        'nursery': NurseryOperation,
        'terminal': NurseryOperation,
        'pollen': PollenProduction,
    }

    LABEL_MAP = {
        'distribution': 'Hybrid_Distribution',
        'harvest': 'Monthly_Harvest',
        'nursery': 'Nursery_Operations',
        'terminal': 'Terminal_Report',
        'pollen': 'Pollen_Production',
    }

    model = MODEL_MAP.get(data_type)
    label = LABEL_MAP.get(data_type, data_type)

    if not model:
        messages.error(request, 'Invalid data type.')
        return redirect('field_data:overview')

    # Security: Ensure supervisors can only delete records in their site
    profile = request.user.profile
    is_admin = profile.role in ('admin', 'superadmin')
    
    # Get the specific object
    try:
        if is_admin:
            obj = model.objects.get(pk=pk)
        else:
            obj = model.objects.get(pk=pk, field_site=profile.field_site)
    except model.DoesNotExist:
        messages.error(request, 'Record not found or you do not have permission to delete it.')
        return redirect('field_data:overview')

    # For Nursery/Terminal, also ensure the type checks out 
    if data_type == 'nursery' and obj.report_type != 'operation':
        messages.error(request, 'Invalid record type.')
        return redirect('field_data:nursery_list')
    if data_type == 'terminal' and obj.report_type != 'terminal':
        messages.error(request, 'Invalid record type.')
        return redirect('field_data:terminal_list')

    # URL to redirect to upon cancel or successful delete
    list_url = f'field_data:{data_type}_list'

    if request.method == 'POST':
        # Log deletion
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            model_name=label,
            object_id=obj.pk,
            details={
                'type': data_type,
                'field_site': obj.field_site.name if obj.field_site else 'Unknown',
                'record_info': str(obj)
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        obj.delete()
        messages.success(request, f'{label.replace("_", " ")} record deleted successfully.')
        return redirect(list_url)

    # Render confirmation page for GET requests
    context = {
        'data_type': label.replace("_", " "),
        'object': obj,
        'cancel_url': request.build_absolute_uri('..')  # Basic fallback, though we can use reverse(list_url)
    }
    
    from django.urls import reverse
    try:
        context['cancel_url'] = reverse(list_url)
    except Exception:
        pass
    return render(request, 'field_data/confirm_delete.html', context)


@login_required
def change_status(request, data_type, pk, new_status):
    """Update approval status of a field data record."""
    from django.utils import timezone
    MODEL_MAP = {
        'distribution': HybridDistribution,
        'harvest': MonthlyHarvest,
        'nursery': NurseryOperation,
        'terminal': NurseryOperation,
        'pollen': PollenProduction,
    }
    
    model = MODEL_MAP.get(data_type)
    if not model:
        messages.error(request, 'Invalid data type.')
        return redirect('field_data:overview')
        
    record = get_object_or_404(model, pk=pk)
    role = getattr(request.user, 'profile', None)
    role = role.role if role else ''
    
    valid_actions = {
        'prepared': ['supervisor', 'admin', 'superadmin', 'sysadmin'],
        'reviewed': ['admin', 'superadmin', 'sysadmin'],
        'noted': ['superadmin', 'sysadmin'],
        'returned': ['admin', 'superadmin', 'sysadmin'],
    }
    
    if new_status not in valid_actions or role not in valid_actions[new_status]:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect(request.META.get('HTTP_REFERER', 'field_data:overview'))

    # Trapping Logic (Maker-Checker Validation)
    if new_status == 'reviewed' and record.prepared_by == request.user:
        messages.error(request, 'Trapping: You cannot review a record you prepared yourself.')
        return redirect(request.META.get('HTTP_REFERER', 'field_data:overview'))
    
    if new_status == 'noted' and (record.prepared_by == request.user or record.reviewed_by == request.user):
        messages.error(request, 'Trapping: You cannot note a record you previously signed.')
        return redirect(request.META.get('HTTP_REFERER', 'field_data:overview'))
        
    msg = ""
    if new_status == 'prepared':
        # Attribution: If not a supervisor, try to find the site's supervisor
        sig_user = request.user
        if role != 'supervisor' and record.field_site:
            supervisor = User.objects.filter(profile__field_site=record.field_site, profile__role='supervisor').first()
            if supervisor:
                sig_user = supervisor
        
        record.status = 'prepared'
        record.prepared_by = sig_user
        record.date_prepared = timezone.now()
        msg = f'Record submitted for review (Prepared by {sig_user.get_full_name() or sig_user.username}).'

    elif new_status == 'reviewed':
        # Attribution: If a Chief (superadmin/sysadmin), try to find an Admin for the site
        sig_user = request.user
        if role in ('superadmin', 'sysadmin') and record.field_site:
            admin_user = User.objects.filter(profile__field_site=record.field_site, profile__role='admin').first()
            if admin_user:
                sig_user = admin_user

        record.status = 'reviewed'
        record.reviewed_by = sig_user
        record.date_reviewed = timezone.now()
        msg = f'Record successfully reviewed (Reviewed by {sig_user.get_full_name() or sig_user.username}).'

    elif new_status == 'noted':
        record.status = 'noted'
        record.noted_by = request.user
        record.date_noted = timezone.now()
        msg = f'Record successfully noted.'

    elif new_status == 'returned':
        record.status = 'draft'
        # Reset signatories on return to draft
        record.prepared_by = None
        record.date_prepared = None
        record.reviewed_by = None
        record.date_reviewed = None
        record.noted_by = None
        record.date_noted = None
        msg = f'Record returned to draft.'
        # trigger notification for return
        _notify_status_change(request, record, 'returned_to_draft', data_type)
        
    record.save()
    
    # Notify for other status changes (prepared, reviewed, noted handled in above branches)
    if new_status != 'returned':
        _notify_status_change(request, record, new_status, data_type)
        
    messages.success(request, msg)
    
    AuditLog.objects.create(
        user=request.user, action='status_change',
        model_name=model.__name__, object_id=record.pk,
        details={'new_status': new_status},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect(request.META.get('HTTP_REFERER', 'field_data:overview'))
