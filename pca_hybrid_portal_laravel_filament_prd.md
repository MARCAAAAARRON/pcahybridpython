# Product Requirements Document (PRD) — Laravel 11 / Filament v3

## Project Title
PCA Hybridization Portal System

## Version
v3.0 — Codebase-Accurate, Multi-Panel Architecture

## Prepared For
Undergraduate Thesis / Capstone Project

## Prepared By
Marc Arron

## Date
March 2026

---

## 1. Executive Summary

The PCA Hybridization Portal is a multi-panel web application for the Philippine Coconut Authority (PCA) — Region VII. It manages the complete lifecycle of coconut hybridization field data: from data entry by field supervisors, through a multi-stage approval workflow (Prepared → Reviewed → Noted), to PCA-branded Excel/PDF report generation with dynamic signatories.

This PRD translates the existing Django-based implementation into a **Laravel 11 + Filament v3** architecture, mapping every feature, model, view, and business rule to its TALL-stack (Tailwind, Alpine.js, Livewire, Laravel) equivalent.

---

## 2. Technical Architecture

### 2.1 Technology Stack

| Layer | Django (Current) | Laravel (Proposed) |
|---|---|---|
| **Framework** | Django 5.x | Laravel 11.x (PHP 8.3+) |
| **Admin/Panels** | Manual views/templates | Filament v3 (Multi-Panel) |
| **Reactivity** | Vanilla JS / AJAX | Livewire 3 |
| **Client-Side** | Vanilla JS (`main.js`) | Alpine.js |
| **Styling** | Custom CSS (`style.css`) | Tailwind CSS 3 |
| **Database** | PostgreSQL (Supabase) | PostgreSQL (Supabase) |
| **ORM** | Django ORM | Eloquent ORM |
| **Auth** | `django.contrib.auth` + custom `UserProfile` | Laravel Breeze + Filament Shield |
| **Excel Export** | `openpyxl` | Maatwebsite/Laravel-Excel |
| **PDF Generation** | Custom generator | Spatie/Laravel-Pdf (or DomPDF) |
| **Audit Logging** | Custom `AuditLog` model | Spatie/Laravel-Activitylog |
| **Notifications** | Custom `Notification` model | Laravel Database Notifications + Filament Notifications |
| **File Storage** | Django `MEDIA_ROOT` | Laravel Filesystem (S3/local) |
| **Session Mgmt** | Custom `SessionTimeoutMiddleware` | Laravel Session + `config/session.php` |

### 2.2 Multi-Panel Architecture

Filament v3 supports multiple independent panels, each with its own middleware, navigation, and role guard. This maps directly to the 4 role-specific dashboards in the current system.

| Panel | URL Prefix | Target Users | Django Equivalent |
|---|---|---|---|
| **App Panel** | `/app` | Supervisor (COS/Agriculturist) | `dashboard/supervisor.html` |
| **Admin Panel** | `/admin` | Senior Agriculturist (Admin) | `dashboard/admin.html` |
| **Chief Panel** | `/chief` | Division Chief (Superadmin) | `dashboard/superadmin.html` |
| **System Panel** | `/system` | IT System Admin (Sysadmin) | `dashboard/sysadmin.html` |

Each panel is registered in its own `PanelProvider` class (e.g., `AppPanelProvider`, `AdminPanelProvider`), with access controlled via the `canAccessPanel()` method on the `User` model based on `UserProfile.role`.

---

## 3. User Roles & Access Control

### 3.1 Role Definitions

| Role Slug | Display Name | Panel Access | Django Equivalent |
|---|---|---|---|
| `supervisor` | COS / Agriculturist | App Panel | `@role_required('supervisor')` |
| `admin` | Senior Agriculturist | Admin Panel | `@role_required('admin')` |
| `superadmin` | Division Chief | Chief Panel | `@role_required('superadmin')` |
| `sysadmin` | System Administrator | System Panel | `@role_required('sysadmin')` |

### 3.2 Separation of Duties (SoD)

The `sysadmin` role exists solely for IT governance. This user:
- **CAN**: Manage users, view audit logs, monitor sessions.
- **CANNOT**: Access field data, approve reports, or generate exports.
- **Laravel Mapping**: The System Panel will have no Filament Resources for `field_data` or `hybridization` models — ensuring SoD by architecture.

### 3.3 Field-Site Scoping (Application-Level RLS)

Supervisors are assigned to a single `FieldSite`. All data access is scoped:

```php
// Laravel: Global Scope on all field-data models
class FieldSiteScope implements Scope
{
    public function apply(Builder $builder, Model $model): void
    {
        if (auth()->user()?->profile?->role === 'supervisor') {
            $builder->where('field_site_id', auth()->user()->profile->field_site_id);
        }
    }
}
```

> **Django Equivalent**: `_get_field_site_filter()` in `field_data/views.py` and `@field_access_required` decorator.

### 3.4 Database-Level RLS

PostgreSQL Row Level Security policies remain active on all `public` schema tables, providing defense-in-depth beyond the application layer. The `enable_rls.sql` script continues to be applied.

---

## 4. Data Models (Eloquent Schema)

### 4.1 Core Models

#### `FieldSite`
> Django: `accounts/models.py → FieldSite`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigIncrements` | PK |
| `name` | `string(100)` | e.g., "Loay On-Farm" |
| `location` | `string(200)` | Physical address |
| `prepared_by_name` | `string` (nullable) | Override signatory for Prepared |
| `prepared_by_title` | `string` (nullable) | Override title |
| `reviewed_by_name` | `string` (nullable) | Override signatory for Reviewed |
| `reviewed_by_title` | `string` (nullable) | Override title |
| `noted_by_name` | `string` (nullable) | Override signatory for Noted |
| `noted_by_title` | `string` (nullable) | Override title |
| `prepared_by_label` | `string` (nullable) | Custom label text |
| `reviewed_by_label` | `string` (nullable) | Custom label text |
| `noted_by_label` | `string` (nullable) | Custom label text |

#### `UserProfile`
> Django: `accounts/models.py → UserProfile` (OneToOne with `User`)

| Column | Type | Notes |
|---|---|---|
| `user_id` | `foreignId` | FK → `users` |
| `role` | `enum` | `supervisor`, `admin`, `superadmin`, `sysadmin` |
| `field_site_id` | `foreignId` (nullable) | FK → `field_sites` |
| `middle_initial` | `string(10)` (nullable) | For signatory formatting |
| `signature_image` | `string` (nullable) | Path to uploaded signature |

#### `Notification`
> Django: `accounts/models.py → Notification`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `foreignId` | FK → `users` |
| `message` | `text` | Notification body |
| `link` | `string` (nullable) | URL to navigate to |
| `is_read` | `boolean` | Default: `false` |
| `created_at` | `timestamp` | Auto-set |

**Laravel Alternative**: Use Laravel's built-in `DatabaseNotification` system via `$user->notify(new ReportPrepared($record))`. Filament's Notification Manager handles the UI.

#### `AuditLog`
> Django: `audit/models.py → AuditLog`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `foreignId` (nullable) | FK → `users` |
| `action` | `string(20)` | `login`, `logout`, `create`, `update`, `delete`, `submit`, `validate`, `revision`, `report`, `user_mgmt`, `export`, `status_change` |
| `model_name` | `string(100)` | e.g., `HybridDistribution` |
| `object_id` | `integer` (nullable) | PK of affected record |
| `details` | `json` | Structured event metadata |
| `ip_address` | `string` (nullable) | Client IP |
| `timestamp` | `timestamp` | Auto-set |

**Laravel Alternative**: Replace with `spatie/laravel-activitylog` for automatic model event logging.

---

### 4.2 Approval Tracking (Abstract Model)

> Django: `field_data/models.py → ApprovalTrackingModel`

All field data models and the `HybridizationRecord` inherit from this abstract:

| Column | Type | Notes |
|---|---|---|
| `status` | `enum` | `draft`, `prepared`, `reviewed`, `noted`, `returned` |
| `prepared_by` | `foreignId` (nullable) | FK → `users` |
| `date_prepared` | `datetime` (nullable) | |
| `reviewed_by` | `foreignId` (nullable) | FK → `users` |
| `date_reviewed` | `datetime` (nullable) | |
| `noted_by` | `foreignId` (nullable) | FK → `users` |
| `date_noted` | `datetime` (nullable) | |
| `created_at` | `timestamp` | Auto-set |
| `updated_at` | `timestamp` | Auto-set |

**Laravel Mapping**: Use an Eloquent Trait `HasApprovalWorkflow`:

```php
trait HasApprovalWorkflow
{
    public function preparedBy(): BelongsTo { return $this->belongsTo(User::class, 'prepared_by'); }
    public function reviewedBy(): BelongsTo { return $this->belongsTo(User::class, 'reviewed_by'); }
    public function notedBy(): BelongsTo { return $this->belongsTo(User::class, 'noted_by'); }
}
```

---

### 4.3 Field Data Models

#### 4.3.1 `HybridDistribution`
> Django: `field_data/models.py → HybridDistribution`

Tracks dispatched seedlings to individual farmer participants.

| Column | Type |
|---|---|
| `field_site_id` | FK → `field_sites` |
| `report_month` | `date` |
| `region` | `string` (default: "VII") |
| `province` | `string` (default: "BOHOL") |
| `district` | `string` |
| `municipality` | `string` |
| `barangay` | `string` |
| `farmer_last_name` | `string` |
| `farmer_first_name` | `string` |
| `farmer_middle_initial` | `string` |
| `is_male` | `boolean` |
| `is_female` | `boolean` |
| `farm_barangay` | `string` |
| `farm_municipality` | `string` |
| `farm_province` | `string` |
| `seedlings_received` | `string` |
| `date_received` | `date` (nullable) |
| `variety` | `string` |
| `seedlings_planted` | `integer` |
| `date_planted` | `date` (nullable) |
| `remarks` | `text` |
| + `ApprovalTracking` fields | (inherited) |

**Special Behavior**: The create form accepts **multiple farmer rows at once** (dynamic repeater), each saved as a separate `HybridDistribution` record. In Filament, this maps to a **Repeater** field in a custom Create page.

---

#### 4.3.2 `MonthlyHarvest`
> Django: `field_data/models.py → MonthlyHarvest`

Parent record for monthly seednut production.

| Column | Type |
|---|---|
| `field_site_id` | FK → `field_sites` |
| `report_month` | `date` |
| `location` | `string` |
| `farm_name` | `string` |
| `area_ha` | `string` (text-based for flexible input) |
| `age_of_palms` | `string` |
| `num_hybridized_palms` | `integer` |
| `remarks` | `text` |
| + `ApprovalTracking` fields | (inherited) |

**Child**: `HarvestVariety` (1:N)

| Column | Type |
|---|---|
| `harvest_id` | FK → `monthly_harvests` |
| `variety` | `string` (e.g., "PCA 15-10") |
| `seednuts_type` | `string` (e.g., "Embryo Cultured") |
| `seednuts_count` | `integer` |
| `remarks` | `string` |

**Filament Mapping**: Use a `Repeater` component for varieties inside the Harvest form.

---

#### 4.3.3 `NurseryOperation` (3-Level Hierarchy)
> Django: `field_data/models.py → NurseryOperation + NurseryBatch + NurseryBatchVariety`

This is the most complex model, implementing a **three-level nested hierarchy**.

**Level 1: `NurseryOperation`**

| Column | Type | Notes |
|---|---|---|
| `field_site_id` | FK | |
| `report_month` | `date` | |
| `report_type` | `enum` | `operation` or `terminal` |
| `region_province_district` | `string` | e.g., "VII-Bohol/III" |
| `barangay_municipality` | `string` | |
| `proponent_entity` | `string` | Nursery entity name |
| `proponent_representative` | `string` | Representative name |
| `target_seednuts` | `integer` | |
| `nursery_start_date` | `date` (nullable) | Terminal reports only |
| `date_ready_for_distribution` | `date` (nullable) | |
| `distribution_remarks` | `text` | |
| + `ApprovalTracking` fields | (inherited) |

**Level 2: `NurseryBatch`** (1:N under `NurseryOperation`)

| Column | Type |
|---|---|
| `nursery_id` | FK → `nursery_operations` |
| `seednuts_harvested` | `integer` |
| `date_harvested` | `string` |
| `date_received` | `string` |
| `source_of_seednuts` | `string` |

**Level 3: `NurseryBatchVariety`** (1:N under `NurseryBatch`)

| Column | Type |
|---|---|
| `batch_id` | FK → `nursery_batches` |
| `variety` | `string` (e.g., "PCA 15-10") |
| `seednuts_sown` | `integer` |
| `date_sown` | `string` |
| `seedlings_germinated` | `integer` |
| `ungerminated_seednuts` | `integer` |
| `culled_seedlings` | `integer` |
| `good_seedlings` | `integer` |
| `ready_to_plant` | `integer` |
| `seedlings_dispatched` | `integer` |
| `remarks` | `string` |

**Filament Mapping**: Nested `Repeater` components — an outer Repeater for Batches, each containing an inner Repeater for Varieties. Summary totals computed via Alpine.js.

> **Note**: The same `NurseryOperation` model is used for both **Nursery Operation Reports** (`report_type='operation'`) and **Terminal Reports** (`report_type='terminal'`). These are displayed as separate Filament Resources with scoped queries.

---

#### 4.3.4 `PollenProduction`
> Django: `field_data/models.py → PollenProduction`

Tracks pollen inventory and weekly utilization.

| Column | Type |
|---|---|
| `field_site_id` | FK → `field_sites` |
| `report_month` | `date` |
| `month_label` | `string` (e.g., "Jan") |
| `pollen_variety` | `string` |
| `ending_balance_prev` | `string` |
| `pollen_source` | `string` |
| `date_received` | `date` (nullable) |
| `pollens_received` | `string` |
| `week1` through `week5` | `string` |
| `total_utilization` | `string` |
| `ending_balance` | `string` |
| `remarks` | `text` |
| + `ApprovalTracking` fields | (inherited) |

---

### 4.4 Hybridization Module

#### `HybridizationRecord`
> Django: `hybridization/models.py → HybridizationRecord`

Core scientific data record for coconut hybridization activities.

| Column | Type | Notes |
|---|---|---|
| `field_site_id` | FK → `field_sites` | |
| `created_by` | FK → `users` | |
| `crop_type` | `string(100)` | |
| `parent_line_a` | `string(100)` | Parent Line A |
| `parent_line_b` | `string(100)` | Parent Line B |
| `hybrid_code` | `string(50)` | Unique identifier |
| `date_planted` | `date` | |
| `growth_status` | `enum` | `seedling`, `vegetative`, `flowering`, `fruiting`, `harvested` |
| `notes` | `text` | |
| `admin_remarks` | `text` | Remarks from reviewer |
| + `ApprovalTracking` fields | (inherited) |

**Child**: `RecordImage` (1:N)

| Column | Type |
|---|---|
| `record_id` | FK → `hybridization_records` |
| `image` | `string` (file path) |
| `caption` | `string(200)` |

---

### 4.5 Reports Module

#### `Report`
> Django: `reports/models.py → Report`

Stores generated report files for download history.

| Column | Type |
|---|---|
| `generated_by` | FK → `users` |
| `report_type` | `enum` | `pdf`, `excel` |
| `field_site_id` | FK (nullable) |
| `title` | `string` |
| `file` | `string` (file path) |
| `created_at` | `timestamp` |

---

## 5. Approval Workflow

### 5.1 Status Flow

```
Draft → Prepared → Reviewed → Noted
  ↑                              |
  └──── Returned (reset) ────────┘
```

### 5.2 Role Permissions per Action

| Action | Allowed Roles | Constraint |
|---|---|---|
| **Prepare** | `supervisor`, `admin`, `superadmin` | Any authorized user |
| **Review** | `admin`, `superadmin` | ⛔ Cannot review own Prepared record (maker-checker) |
| **Note** | `superadmin` | ⛔ Cannot note if you Prepared or Reviewed (maker-checker) |
| **Return to Draft** | `admin`, `superadmin` | Resets all signatories |

### 5.3 Maker-Checker Trapping Logic (Critical)

> Django: `field_data/views.py → change_status()`, Lines 1628–1635

```php
// Filament Action Guard
if ($newStatus === 'reviewed' && $record->prepared_by === auth()->id()) {
    Notification::make()->danger()->title('Trapping: You cannot review a record you prepared.')->send();
    return;
}
if ($newStatus === 'noted' && in_array(auth()->id(), [$record->prepared_by, $record->reviewed_by])) {
    Notification::make()->danger()->title('Trapping: You cannot note a record you previously signed.')->send();
    return;
}
```

### 5.4 Signatory Attribution Logic

When an admin or chief signs a record that "should" belong to a lower role:
- **Preparing as Admin**: System auto-attributes to the site's Supervisor.
- **Reviewing as Chief**: System auto-attributes to the site's Admin.

> Django: `change_status()`, Lines 1639–1657

---

## 6. Feature Specifications

### 6.1 Carry-Forward System

> Django: `field_data/views.py` → `harvest_carry_forward()`, `pollen_carry_forward()`, `nursery_carry_forward()`, `terminal_carry_forward()`

When creating a new record, the system offers a "Carry Forward" button that fetches the most recent record for the same `FieldSite` via AJAX and pre-fills:
- Static metadata (location, farm name, proponent, etc.)
- Next `report_month` (auto-incremented)
- Previous `ending_balance` → new `ending_balance_prev` (Pollen)
- Full batch/variety hierarchy (Nursery/Terminal)

**Laravel Mapping**: Implement as Livewire component actions or API endpoints consumed by Alpine.js on custom Filament Create pages.

### 6.2 Excel Export System

> Django: `field_data/exports.py` (1,057 lines)

Each module has a dedicated exporter producing PCA-branded `.xlsx` files:

| Module | Exporter | Sheet Structure |
|---|---|---|
| Distribution | `export_distribution()` | 1 sheet per FieldSite, 19 columns, PCA header/footer |
| Harvest | `export_harvest()` | 1 sheet per FieldSite, 21 columns, grouped by farm, monthly pivot |
| Nursery | `export_nursery()` | 1 sheet per FieldSite, 18 columns, batch rows merged by parent |
| Terminal | `export_terminal()` | Same as Nursery but with terminal-specific fields |
| Pollen | `export_pollen()` | 1 sheet per FieldSite, 14 columns |

**Common Features**:
- **PCA Logo Header**: Embedded `PCA&DA_Logo.png` via `OneCellAnchor`.
- **Dynamic Footer with Signatories**: Prepared By / Reviewed By / Noted By — names pulled from `FieldSite` overrides or from the record's signatory users.
- **Signature Images**: Uploaded user signatures embedded above their name line.
- **Auto Column Widths**: Computed based on content length.
- **Page Setup**: Letter size, landscape orientation, fit-to-width.

**Laravel Mapping**: Use `Maatwebsite/Laravel-Excel` with custom `WithStyles`, `WithDrawings`, and `WithEvents` concerns. The `AfterSheet` event provides direct `PhpSpreadsheet` access for logo placement and footer signatories.

### 6.3 PDF Report Generation

> Django: `reports/generators.py`

Reports support all 6 modules: Distribution, Harvest, Nursery, Terminal, Pollen, Hybridization. Filtered by FieldSite, month, and year. Generated files are stored in the `Report` model for download history.

**Laravel Mapping**: Spatie/Laravel-Pdf or DomPDF for rendering a Blade view to PDF.

### 6.4 Notification System

> Django: `accounts/models.py → Notification`, `accounts/context_processors.py`, `field_data/views.py → _notify_new_report()`, `_notify_status_change()`

**Notification Events**:

| Event | Recipients | Message Pattern |
|---|---|---|
| New record created | Site Admins (or all Admins) | `[{site}] {user} submitted a new {type} record.` |
| Status → Prepared | Site Admins | `[{site}] {model} report prepared by {user}. Ready for review.` |
| Status → Reviewed | Site Chiefs (superadmin) | `[{site}] {model} report reviewed by {user}. Ready to be noted.` |
| Status → Noted | Preparer + Reviewer | `[{site}] {model} report has been officially noted by {user}.` |
| Status → Returned | Preparer | `[{site}] {model} report was returned to draft by {user}.` |
| Report generated | Self | `{type} report generated: {title}` |

**Bell Icon**: Navbar shows 3 most recent notifications with unread count badge.

**Laravel Mapping**: Laravel Database Notifications + Filament's `DatabaseNotifications` plugin (built-in bell icon with dropdown).

### 6.5 Dashboard Analytics

| Panel | Key Widgets |
|---|---|
| **Supervisor (App)** | Site-specific counts by module, recent activity feed (6 items), bar chart (Chart.js → Filament Chart Widget) |
| **Admin** | Multi-site comparison table, pending validation queue, global module totals, per-site breakdown, bar chart |
| **Chief (Superadmin)** | System-wide overview, per-site field data table, total field sites count, bar chart |
| **Sysadmin** | Total users count, active users count, total field sites, recent audit logs (10 items) |

---

## 7. Middleware & Security

### 7.1 Session Timeout

> Django: `accounts/middleware.py → SessionTimeoutMiddleware`

30-minute inactivity timeout. After expiry, user is auto-logged out and redirected to login.

```php
// Laravel: config/session.php
'lifetime' => 30,
'expire_on_close' => true,
```

### 7.2 Cache Control

> Django: `accounts/middleware.py → CacheControlMiddleware`

Prevent browser back-button from showing data after logout.

```php
// Laravel: Middleware
$response->headers->set('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0');
$response->headers->set('Pragma', 'no-cache');
$response->headers->set('Expires', '0');
```

### 7.3 Password & Auth

- Password validators (min length, common password check, numeric check)
- User's own profile editing with password change
- Signature image upload for export embedding

---

## 8. Filament Resource Mapping

### 8.1 App Panel (Supervisor)

| Resource | Model | Features |
|---|---|---|
| `DistributionResource` | `HybridDistribution` | Repeater for multi-row create, list with totals |
| `HarvestResource` | `MonthlyHarvest` | Repeater for varieties, carry-forward button |
| `NurseryResource` | `NurseryOperation` (scoped: `operation`) | Nested Repeater (Batch → Variety), carry-forward |
| `TerminalResource` | `NurseryOperation` (scoped: `terminal`) | Same as Nursery, separate navigation |
| `PollenResource` | `PollenProduction` | Carry-forward (ending balance → prev balance) |
| `HybridizationResource` | `HybridizationRecord` | Image uploads, growth status tracking |

**Table Actions on every resource**:
- ✏️ Edit
- 🗑️ Delete (with confirmation)
- 📋 Prepare / Review / Note (workflow actions, role-gated)
- 📥 Excel Export (header action)

**Table Filters on every resource**:
- FieldSite (admin only)
- Year
- Month

### 8.2 Admin Panel (Senior Agriculturist)

Same Resources as App Panel, but:
- **Full cross-site visibility** (no `FieldSiteScope`)
- **Review action** enabled
- **Consolidated export** across all sites

### 8.3 Chief Panel (Division Chief)

Same as Admin Panel, plus:
- **Note action** enabled
- **System-wide dashboard** with per-site comparison

### 8.4 System Panel (Sysadmin)

| Resource | Model | Features |
|---|---|---|
| `UserResource` | `User` + `UserProfile` | Create/Edit/Toggle active, inline role change |
| `AuditLogResource` | `AuditLog` | Read-only, searchable, filterable by action/user/date |

**No access to field data or hybridization resources** (SoD enforcement).

---

## 9. Seed Data

> Django: `accounts/management/commands/seed_data.py`

A Laravel seeder (`DatabaseSeeder`) should create:
- 2 FieldSites: "Loay On-Farm", "Balilihan On-Farm" (with default signatories)
- 1 Sysadmin account
- 1 Superadmin (Division Chief) account
- 2 Admin (Senior Agriculturist) accounts, one per site
- 2 Supervisor accounts, one per site

```php
// Laravel: php artisan db:seed
```

---

## 10. Non-Functional Requirements

| Requirement | Specification |
|---|---|
| **Timezone** | `Asia/Manila` (UTC+8) |
| **Page Size** | Export: Letter (8.5"×11"), Landscape |
| **Session** | 30-minute timeout, expire on browser close |
| **Security** | CSRF protection (Laravel default), XSS via Blade auto-escaping, RLS on PostgreSQL |
| **Performance** | Eager-loaded relationships via `with()`, paginated lists (500 max before pagination) |
| **Browser Support** | Modern browsers (Chrome, Edge, Firefox) |
| **Responsive** | Filament's built-in responsive layout |

---

## 11. Future Enhancements (Post-MVP)

1. **Offline mode** with PWA + background sync for remote field sites.
2. **Automated report scheduling** via Laravel queues and task scheduler.
3. **Mobile companion app** using Flutter consuming the same Laravel API.
4. **Advanced analytics** with charting libraries (ApexCharts via Filament Widgets).
5. **Multi-tenancy** for other PCA Regional offices.

---

**End of Document**
