from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.core.files.base import ContentFile
from datetime import datetime

from accounts.decorators import role_required
from accounts.models import FieldSite, Notification
from audit.models import AuditLog
from field_data.models import MonthlyHarvest, NurseryOperation, HybridDistribution, PollenProduction
from hybridization.models import HybridizationRecord
from .models import Report
from .generators import generate_pdf_report, generate_excel_export

@login_required
@role_required('supervisor', 'admin', 'superadmin')
def index(request):
    """Report generation page and history."""
    profile = request.user.profile

    if profile.role == 'supervisor':
        reports = Report.objects.filter(generated_by=request.user)
        field_sites = FieldSite.objects.filter(id=profile.field_site_id) if profile.field_site else FieldSite.objects.none()
    else:
        reports = Report.objects.all()
        field_sites = FieldSite.objects.all()

    return render(request, 'reports/index.html', {
        'reports': reports[:20],
        'field_sites': field_sites,
    })


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def generate_report(request):
    """Generate a PDF or CSV report."""
    if request.method != 'POST':
        return redirect('reports:index')

    profile = request.user.profile
    report_type = request.POST.get('report_type', 'pdf')
    report_module = request.POST.get('report_module', 'harvest')
    field_site_ids = request.POST.getlist('field_site')
    filter_month_str = request.POST.get('filter_month')
    filter_year_str = request.POST.get('filter_year')
    filter_month = int(filter_month_str) if filter_month_str else None
    filter_year = int(filter_year_str) if filter_year_str else None

    # Determine field sites
    field_sites = []
    if profile.role == 'supervisor' and profile.field_site:
        field_sites = [profile.field_site]
    elif field_site_ids and '' not in field_site_ids:
        # User selected specific sites (not "All Sites")
        field_sites = list(FieldSite.objects.filter(id__in=field_site_ids))
    else:
        # "All Sites" selected or no selection
        field_sites = list(FieldSite.objects.all())

    if len(field_sites) == 1:
        site_name = field_sites[0].name
    else:
        site_name = "Multiple Sites"
    
    # Parse dates
    import calendar
    date_range_str = "All Time"
    as_of_date = None
    if filter_month and filter_year:
        month_name = calendar.month_name[filter_month]
        date_range_str = f"{month_name} {filter_year}"
        last_day = calendar.monthrange(filter_year, filter_month)[1]
        as_of_date = datetime(filter_year, filter_month, last_day).date()
    elif filter_year:
        date_range_str = f"Year {filter_year}"
        as_of_date = datetime(filter_year, 12, 31).date()
    elif filter_month:
        month_name = calendar.month_name[filter_month]
        date_range_str = f"All {month_name}s"
        as_of_date = datetime.now().date()

    headers = []
    data = []
    title = ""

    if report_module == 'harvest':
        title = f"Monthly Harvest Report — {site_name}"
        records = MonthlyHarvest.objects.all()
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(report_month__month=filter_month)
        if filter_year:
            records = records.filter(report_month__year=filter_year)
            
        headers = ['Report Month', 'Farm Name', 'Area (Ha)', 'Age of Palms', 'No. Hybridized/Mother', 'Location', 'Total Seednuts']
        for r in records:
            data.append([
                r.report_month.strftime('%Y-%m') if r.report_month else '',
                r.farm_name,
                str(r.area_ha),
                str(r.age_of_palms),
                str(r.num_hybridized_palms),
                r.location,
                str(r.total_seednuts),
            ])
            
    elif report_module == 'nursery':
        title = f"Nursery Operations Report — {site_name}"
        records = NurseryOperation.objects.filter(report_type='operation').prefetch_related('batches')
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(report_month__month=filter_month)
        if filter_year:
            records = records.filter(report_month__year=filter_year)
            
        headers = ['Report Month', 'Entity Name', 'Rep', 'Target', 'Harvested', 'Date Rcvd', 'Source', 'Variety', 'Sown', 'Date Sown', 'Germinated', 'Ungerm', 'Culled', 'Good/1ft', 'Poly', 'Dispatched']
        for r in records:
            batches = r.batches.all()
            if not batches:
                data.append([
                    r.report_month.strftime('%Y-%m') if r.report_month else '',
                    r.proponent_entity,
                    r.proponent_representative[:10] + '...' if len(r.proponent_representative) > 10 else r.proponent_representative,
                    str(r.target_seednuts),
                    '0', '', '', '', '0', '', '0', '0', '0', '0', '0', '0',
                ])
                continue
                
            for batch in batches:
                data.append([
                    r.report_month.strftime('%Y-%m') if r.report_month else '',
                    r.proponent_entity,
                    r.proponent_representative[:10] + '...' if len(r.proponent_representative) > 10 else r.proponent_representative,
                    str(r.target_seednuts),
                    str(batch.seednuts_harvested),
                    batch.date_received.strftime('%m-%d') if batch.date_received else '',
                    batch.source_of_seednuts[:10] + '...' if batch.source_of_seednuts and len(batch.source_of_seednuts) > 10 else (batch.source_of_seednuts or ''),
                    batch.variety,
                    str(batch.seednuts_sown),
                    batch.date_sown.strftime('%m-%d') if batch.date_sown else '',
                    str(batch.seedlings_germinated),
                    str(batch.ungerminated_seednuts),
                    str(batch.culled_seedlings),
                    str(batch.good_seedlings),
                    str(batch.ready_to_plant),
                    str(batch.seedlings_dispatched),
                ])

    elif report_module == 'terminal':
        title = f"Terminal Report — {site_name}"
        records = NurseryOperation.objects.filter(report_type='terminal').prefetch_related('batches')
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(report_month__month=filter_month)
        if filter_year:
            records = records.filter(report_month__year=filter_year)
            
        headers = ['Report Month', 'Entity Name', 'Rep', 'Target', 'Harvested', 'Date Rcvd', 'Source', 'Variety', 'Sown', 'Date Sown', 'Germinated', 'Ungerm', 'Culled', 'Good/1ft', 'Poly', 'Dispatched']
        for r in records:
            batches = r.batches.all()
            if not batches:
                data.append([
                    r.report_month.strftime('%Y-%m') if r.report_month else '',
                    r.proponent_entity,
                    r.proponent_representative[:10] + '...' if len(r.proponent_representative) > 10 else r.proponent_representative,
                    str(r.target_seednuts),
                    '0', '', '', '', '0', '', '0', '0', '0', '0', '0', '0',
                ])
                continue
                
            for batch in batches:
                data.append([
                    r.report_month.strftime('%Y-%m') if r.report_month else '',
                    r.proponent_entity,
                    r.proponent_representative[:10] + '...' if len(r.proponent_representative) > 10 else r.proponent_representative,
                    str(r.target_seednuts),
                    str(batch.seednuts_harvested),
                    batch.date_received.strftime('%m-%d') if batch.date_received else '',
                    batch.source_of_seednuts[:10] + '...' if batch.source_of_seednuts and len(batch.source_of_seednuts) > 10 else (batch.source_of_seednuts or ''),
                    batch.variety,
                    str(batch.seednuts_sown),
                    batch.date_sown.strftime('%m-%d') if batch.date_sown else '',
                    str(batch.seedlings_germinated),
                    str(batch.ungerminated_seednuts),
                    str(batch.culled_seedlings),
                    str(batch.good_seedlings),
                    str(batch.ready_to_plant),
                    str(batch.seedlings_dispatched),
                ])

    elif report_module == 'distribution':
        title = f"Hybrid Distribution Report — {site_name}"
        records = HybridDistribution.objects.all()
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(report_month__month=filter_month)
        if filter_year:
            records = records.filter(report_month__year=filter_year)
            
        headers = ['Report Month', 'Farmer', 'Barangay', 'Municipality', 'Province', 'Received', 'Planted', 'Variety', 'Date Planted', 'Remarks']
        for r in records:
            data.append([
                r.report_month.strftime('%Y-%m') if r.report_month else '',
                f"{r.farmer_last_name}, {r.farmer_first_name} {r.farmer_middle_initial}",
                r.barangay,
                r.municipality,
                r.province,
                str(r.seedlings_received),
                str(r.seedlings_planted),
                r.variety,
                str(r.date_planted),
                r.remarks[:10] + '...' if r.remarks and len(r.remarks) > 10 else (r.remarks or ''),
            ])

    elif report_module == 'pollen':
        title = f"Pollen Production Report — {site_name}"
        records = PollenProduction.objects.all()
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(report_month__month=filter_month)
        if filter_year:
            records = records.filter(report_month__year=filter_year)
            
        headers = ['Report Month', 'Month Label', 'Prev Balance', 'Received', 'Utilization', 'Ending Balance']
        for r in records:
            data.append([
                r.report_month.strftime('%Y-%m') if r.report_month else '',
                r.month_label,
                str(r.ending_balance_prev),
                str(r.pollens_received),
                str(r.total_utilization),
                str(r.ending_balance),
            ])

    elif report_module == 'hybridization':
        title = f"Hybridization Records Report — {site_name}"
        records = HybridizationRecord.objects.all()
        if field_sites:
            records = records.filter(field_site__in=field_sites)
        if filter_month:
            records = records.filter(date_planted__month=filter_month)
        if filter_year:
            records = records.filter(date_planted__year=filter_year)

        headers = ['Hybrid Code', 'Crop Type', 'Parent Line A', 'Parent Line B', 'Date Planted', 'Growth Status', 'Status', 'Field Site', 'Created By']
        for r in records:
            data.append([
                r.hybrid_code,
                r.crop_type,
                r.parent_line_a,
                r.parent_line_b,
                r.date_planted.strftime('%Y-%m-%d') if r.date_planted else '',
                r.get_growth_status_display(),
                r.get_status_display(),
                str(r.field_site) if r.field_site else '',
                r.created_by.get_full_name() or r.created_by.username,
            ])
            
    else:
        messages.error(request, 'Invalid report module.')
        return redirect('reports:index')

    if not records.exists():
        messages.warning(request, f'No data available for {title} with the selected filters.')
        return redirect('reports:index')

    if report_type == 'pdf':
        buffer = generate_pdf_report(headers=headers, data=data, field_sites=field_sites, title=title, date_range_str=date_range_str, records=records)

        # Save to Report model
        report_title = f"{title} ({report_module.title()})"
        report = Report(
            generated_by=request.user,
            report_type='pdf',
            field_site=field_sites[0] if len(field_sites) == 1 else None,
            title=report_title,
        )
        report.file.save(
            f"report_{report_module}_{site_name.lower().replace(' ', '_')}.pdf",
            ContentFile(buffer.read()),
        )
        report.save()

        # Return the file
        report.file.open('rb')
        response = FileResponse(report.file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.file.name.split("/")[-1]}"'

    elif report_type == 'excel':
        from .generators import generate_excel_export
        buffer = generate_excel_export(report_module, records, as_of_date=as_of_date)

        report_title = f"{title} ({report_module.title()})"
        report = Report(
            generated_by=request.user,
            report_type='excel',
            field_site=field_sites[0] if len(field_sites) == 1 else None,
            title=report_title,
        )
        report.file.save(
            f"export_{report_module}_{site_name.lower().replace(' ', '_')}.xlsx",
            ContentFile(buffer.getvalue()),
        )
        report.save()

        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{report.file.name.split("/")[-1]}"'

    else:
        messages.error(request, 'Invalid report type.')
        return redirect('reports:index')

    # Audit log
    AuditLog.objects.create(
        user=request.user,
        action='report',
        model_name='Report',
        object_id=report.id,
        details={'type': report_type, 'field_site': site_name},
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # Notification
    Notification.objects.create(
        user=request.user,
        message=f'{report_type.upper()} report generated: {title}',
    )

    return response


@login_required
@role_required('supervisor', 'admin', 'superadmin')
def download_report(request, pk):
    """Download a previously generated report."""
    report = Report.objects.get(pk=pk)

    # Access check
    if request.user.profile.role == 'supervisor' and report.generated_by != request.user:
        messages.error(request, 'Access denied.')
        return redirect('reports:index')

    report.file.open('rb')
    content_type = 'application/pdf' if report.report_type == 'pdf' else 'text/csv'
    response = FileResponse(report.file, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{report.file.name.split("/")[-1]}"'
    return response
