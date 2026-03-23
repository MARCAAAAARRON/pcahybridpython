from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q

from accounts.models import Notification
from accounts.decorators import role_required
from hybridization.models import HybridizationRecord
from accounts.models import FieldSite
from audit.models import AuditLog
from field_data.models import MonthlyHarvest, NurseryOperation, HybridDistribution, PollenProduction


def get_common_context(request):
    """Return notifications and unread count for the navbar."""
    notifications = Notification.objects.filter(user=request.user)[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'notifications': notifications,
        'unread_notification_count': unread_count,
    }


@login_required
def index(request):
    """Route to the correct dashboard based on user role."""
    role = request.user.profile.role
    if role == 'supervisor':
        return supervisor_dashboard(request)
    elif role == 'admin':
        return admin_dashboard(request)
    elif role == 'superadmin':
        return superadmin_dashboard(request)
    elif role == 'sysadmin':
        return sysadmin_dashboard(request)
    return render(request, 'dashboard/supervisor.html')


def supervisor_dashboard(request):
    """Dashboard for supervisors — field-specific data only."""
    field_site = request.user.profile.field_site

    # If the supervisor has a field site, filter by it; otherwise show all data
    if field_site:
        records = HybridizationRecord.objects.filter(field_site=field_site)
        harvest_records = MonthlyHarvest.objects.filter(field_site=field_site)
        pollen_records = PollenProduction.objects.filter(field_site=field_site)
        nursery_records = NurseryOperation.objects.filter(field_site=field_site, report_type='operation')
        terminal_records = NurseryOperation.objects.filter(field_site=field_site, report_type='terminal')
        distribution_records = HybridDistribution.objects.filter(field_site=field_site)
    else:
        records = HybridizationRecord.objects.all()
        harvest_records = MonthlyHarvest.objects.all()
        pollen_records = PollenProduction.objects.all()
        nursery_records = NurseryOperation.objects.filter(report_type='operation')
        terminal_records = NurseryOperation.objects.filter(report_type='terminal')
        distribution_records = HybridDistribution.objects.all()

    stats = {
        'total': records.count(),
        'draft': records.filter(status='draft').count(),
        'submitted': records.filter(status='submitted').count(),
        'validated': records.filter(status='validated').count(),
    }
    recent_records = records[:5]

    field_stats = {
        'harvest_count': harvest_records.count(),
        'pollen_count': pollen_records.count(),
        'nursery_count': nursery_records.count(),
        'terminal_count': terminal_records.count(),
        'distribution_count': distribution_records.count(),
    }

    # Aggregate recent activity across the 4 field data models
    recent_activities = []
    for r in harvest_records.order_by('-created_at')[:5]:
        recent_activities.append({'type': 'Harvest', 'date': r.created_at, 'user': 'System', 'desc': str(r)})
    for r in pollen_records.order_by('-created_at')[:5]:
        recent_activities.append({'type': 'Pollen', 'date': r.created_at, 'user': 'System', 'desc': str(r)})
    for r in nursery_records.order_by('-report_month')[:5]:
        recent_activities.append({'type': 'Nursery', 'date': r.report_month, 'user': 'System', 'desc': str(r)})
    for r in distribution_records.order_by('-created_at')[:5]:
        recent_activities.append({'type': 'Distribution', 'date': r.created_at, 'user': 'System', 'desc': str(r)})
    
    # Sort and take top 5
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:6]

    chart_labels = ['Harvest', 'Nursery', 'Distribution', 'Terminal Report', 'Pollen']
    chart_data = [
        field_stats['harvest_count'],
        field_stats['nursery_count'],
        field_stats['distribution_count'],
        field_stats['terminal_count'],
        field_stats['pollen_count']
    ]

    ctx = get_common_context(request)
    ctx.update({
        'field_site': field_site,
        'stats': stats,
        'recent_records': recent_records,
        'field_stats': field_stats,
        'recent_activities': recent_activities,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })
    return render(request, 'dashboard/supervisor.html', ctx)


def admin_dashboard(request):
    """Dashboard for admins — multi-field overview."""
    all_records = HybridizationRecord.objects.all()
    field_sites = FieldSite.objects.all()

    # Per-field stats
    field_stats = []
    for site in field_sites:
        site_records = all_records.filter(field_site=site)
        field_stats.append({
            'site': site,
            'total': site_records.count(),
            'submitted': site_records.filter(status='submitted').count(),
            'validated': site_records.filter(status='validated').count(),
        })

    pending_validations = all_records.filter(status='submitted')

    global_field_stats = {
        'harvest_count': MonthlyHarvest.objects.all().count(),
        'pollen_count': PollenProduction.objects.all().count(),
        'nursery_count': NurseryOperation.objects.filter(report_type='operation').count(),
        'terminal_count': NurseryOperation.objects.filter(report_type='terminal').count(),
        'distribution_count': HybridDistribution.objects.all().count(),
    }
    global_field_stats['total_count'] = sum(global_field_stats.values())

    # Per-site field data breakdown
    per_site_field_stats = []
    for site in field_sites:
        stats_dict = {
            'site': site,
            'harvest': MonthlyHarvest.objects.filter(field_site=site).count(),
            'pollen': PollenProduction.objects.filter(field_site=site).count(),
            'nursery': NurseryOperation.objects.filter(field_site=site, report_type='operation').count(),
            'terminal': NurseryOperation.objects.filter(field_site=site, report_type='terminal').count(),
            'distribution': HybridDistribution.objects.filter(field_site=site).count(),
        }
        stats_dict['total'] = stats_dict['harvest'] + stats_dict['pollen'] + stats_dict['nursery'] + stats_dict['terminal'] + stats_dict['distribution']
        per_site_field_stats.append(stats_dict)

    chart_labels = ['Harvest', 'Nursery', 'Distribution', 'Terminal Report', 'Pollen']
    chart_data = [
        global_field_stats['harvest_count'],
        global_field_stats['nursery_count'],
        global_field_stats['distribution_count'],
        global_field_stats['terminal_count'],
        global_field_stats['pollen_count']
    ]

    ctx = get_common_context(request)
    ctx.update({
        'total_records': all_records.count(),
        'field_stats': field_stats,
        'global_field_stats': global_field_stats,
        'per_site_field_stats': per_site_field_stats,
        'pending_validations': pending_validations[:10],
        'pending_count': pending_validations.count(),
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })
    return render(request, 'dashboard/admin.html', ctx)


def superadmin_dashboard(request):
    """Dashboard for super admins — system overview."""
    field_sites = FieldSite.objects.all()

    global_field_stats = {
        'harvest_count': MonthlyHarvest.objects.all().count(),
        'pollen_count': PollenProduction.objects.all().count(),
        'nursery_count': NurseryOperation.objects.filter(report_type='operation').count(),
        'terminal_count': NurseryOperation.objects.filter(report_type='terminal').count(),
        'distribution_count': HybridDistribution.objects.all().count(),
    }
    global_field_stats['total_count'] = sum(global_field_stats.values())

    # Per-site field data breakdown
    per_site_field_stats = []
    for site in field_sites:
        stats_dict = {
            'site': site,
            'harvest': MonthlyHarvest.objects.filter(field_site=site).count(),
            'pollen': PollenProduction.objects.filter(field_site=site).count(),
            'nursery': NurseryOperation.objects.filter(field_site=site, report_type='operation').count(),
            'terminal': NurseryOperation.objects.filter(field_site=site, report_type='terminal').count(),
            'distribution': HybridDistribution.objects.filter(field_site=site).count(),
        }
        stats_dict['total'] = stats_dict['harvest'] + stats_dict['pollen'] + stats_dict['nursery'] + stats_dict['terminal'] + stats_dict['distribution']
        per_site_field_stats.append(stats_dict)

    chart_labels = ['Harvest', 'Nursery', 'Distribution', 'Terminal Report', 'Pollen']
    chart_data = [
        global_field_stats['harvest_count'],
        global_field_stats['nursery_count'],
        global_field_stats['distribution_count'],
        global_field_stats['terminal_count'],
        global_field_stats['pollen_count']
    ]

    ctx = get_common_context(request)
    ctx.update({
        'total_records': HybridizationRecord.objects.count(),
        'total_field_sites': FieldSite.objects.count(),
        'global_field_stats': global_field_stats,
        'per_site_field_stats': per_site_field_stats,
        'field_sites': field_sites,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })
    return render(request, 'dashboard/superadmin.html', ctx)

def sysadmin_dashboard(request):
    """Dashboard for system admins — strictly user management and audit logs."""
    ctx = get_common_context(request)
    ctx.update({
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_field_sites': FieldSite.objects.count(),
        'recent_logs': AuditLog.objects.select_related('user')[:10],
    })
    return render(request, 'dashboard/sysadmin.html', ctx)
