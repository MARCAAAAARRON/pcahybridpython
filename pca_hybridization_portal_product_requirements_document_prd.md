# Product Requirements Document (PRD)

## Project Title
PCA Hybridization Portal System

## Version
v3.0 (Updated - Final Implementation)

## Prepared For
Undergraduate Thesis / Capstone Project

## Prepared By
Marc Arron

---

## 1. Purpose of the Document
This Product Requirements Document (PRD) specifies the complete functional and non-functional requirements of the PCA Hybridization Portal System. It serves as the authoritative reference for system design, development, testing, deployment, and thesis defense, reflecting the final implemented architecture and security measures.

---

## 2. Project Overview

### 2.1 System Description
The PCA Hybridization Portal System is a secure, enterprise-grade information system designed to manage coconut hybridization activities across multiple Philippine Coconut Authority (PCA) field sites. It features a robust multi-level data hierarchy, role-based access control with Separation of Duties (SoD), Row Level Security (RLS) for database protection, and automated professional reporting in Excel and PDF formats.

### 2.2 Background and Rationale
Traditional manual spreadsheet-based recording led to fragmented data, poor traceability, and transcription errors. This system centralizes field data — including seedling distribution, seednut harvest, multi-phase nursery operations, and pollen production — while enforcing strict accountability through digital signatures and a comprehensive audit trail.

### 2.3 Objectives
- **Digitize & Centralize**: Centralize PCA hybridization records across all field sites (Loay, Balilihan, etc.).
- **Enforce Access Governance**: Implement field-based isolation and role-specific permissions.
- **Implement SoD**: Separate agricultural data management from system administration and user governance.
- **Support Complex Operations**: Manage a 3-level nursery data hierarchy and carry-forward logic for monthly modules.
- **Automate Professional Reporting**: Generate PCA-branded reports with dynamic signatories and official branding.
- **Ensure Data Integrity**: Use RLS to prevent unauthorized direct database access.

---

## 3. Scope

### 3.1 In Scope
- **Authentication**: Secure login with 30-minute inactivity timeout.
- **Role-Based Access**: Specialized roles (Supervisor, Admin, Chief, SysAdmin).
- **Core Modules**: Hybrid Distribution, Monthly Harvest, Nursery Operations (3-level), Pollen Production.
- **Workflow Management**: Draft → Prepared → Reviewed → Noted lifecycle for records.
- **Security**: Row Level Security (RLS) on Supabase PostgreSQL.
- **Reporting**: Dynamic Excel/PDF exports with logo, headers, and footer signatories.
- **Notifications**: In-app alerts for record status updates and submissions.
- **Audit Logs**: Full traceability of all user actions.
- **Premium UI**: Modern, responsive dashboard with interactive data visualization.

### 3.2 Out of Scope
- Public-facing APIs (system is strictly internal).
- External email/SMS gateways (notifications are in-app only).
- AI-based predictive analytics (focus is on record management and reporting).

---

## 4. Stakeholders

| Stakeholder | Role Title | Responsibility |
|------------|------------|----------------|
| Farm Supervisor | COS / Agriculturist | Field-level data entry, monitoring, and report preparation. |
| Admin | Senior Agriculturist | Cross-field data review, validation (Reviewing), and reporting. |
| Super Admin | PCDM / Division Chief I | Executive oversight, final approval (Noting), and analytical review. |
| System Admin | IT Administrator | User account governance, role assignment, and audit log monitoring. |

---

## 5. User Roles and Permissions (Separation of Duties)

### 5.1 Supervisor (COS / Agriculturist)
- **Scope**: Assigned to one site (e.g., Loay).
- **Actions**: CRUD own records, prepare reports for review.
- **Restrictions**: Cannot view other sites or manage users.

### 5.2 Admin (Senior Agriculturist)
- **Scope**: All field sites.
- **Actions**: Review data, generate consolidated reports, request revisions.
- **Restrictions**: Cannot manage user roles or view system audit logs.

### 5.3 Super Admin (PCDM / Division Chief I)
- **Scope**: All field sites.
- **Actions**: Final approval of reports ("Noting"), view executive dashboards.
- **Restrictions**: Limited to data oversight; does not manage user accounts.

### 5.4 System Administrator (IT Admin)
- **Scope**: System-level.
- **Actions**: Manage user accounts, role assignments, site assignments, and Audit Logs.
- **Restrictions**: **Strictly Blocked** from viewing agricultural data and dashboards. This ensures a person managing accounts cannot falsify field records.

---

## 6. Functional Requirements

### 6.1 Authentication & Security Implementation
- **Role-Based Access Control (RBAC)**: Enforced via custom Django decorators (`@role_required`).
- **Field-Based Isolation**: Enforced at the QuerySet level; Supervisors only see assigned site data.
- **Row Level Security (RLS)**: Enabled on Supabase to deny direct access via PostgREST, ensuring only the Django backend can interact with core tables.
- **Session Management**: 30-minute timeout and cache-control headers prevent unauthorized back-button access.

### 6.2 The 3-Level Nursery Hierarchy
The system supports a granular data structure for nursery operations to ensure detailed traceability:
1.  **Nursery Operation (Header)**: General proponent, location, and target information.
2.  **Nursery Batch (Child)**: Specific harvest events (Date, Source, Total Seednuts).
3.  **Batch Variety (Grandchild)**: Detailed counts per variety within a batch (Sown, Germinated, Culled, Ready to Plant, Dispatched).

### 6.3 Notification System
- **Triggers**: Automated notifications for record status changes (e.g., "Report Returned for Revision" or "Report Noted by Chief").
- **UI**: Navbar bell icon with unread count badge.
- **Navigation**: Clickable notifications lead directly to the relevant record for immediate action.

### 6.4 Professional Reporting & Dynamic Signatories
- **Dynamic Signatories**: `FieldSite` model stores custom labels/names/titles for "Prepared by", "Reviewed by", and "Noted by" sections.
- **Excel Export**: High-fidelity `.xlsx` with official logos, color-coded headers, and auto-calculated totals.
- **PDF Generation**: ReportLab-powered landscape reports for formal archiving and signing.

---

## 7. Non-Functional Requirements

### 7.1 Security & Data Integrity
- **RLS**: Mandatory for all sensitive tables on Supabase.
- **CSRF**: Middleware enabled for all data-modifying requests.
- **Auditability**: JSON-detailed logs for every Create, Update, and Delete action.

### 7.2 Performance & UI Aesthetics
- **Premium Design**: Vibrant PCA green accents, modern typography (Inter/Outfit), and glassmorphism-inspired UI components.
- **Usability**: AJAX-powered carry-forward logic reduces manual entry by 70% for monthly reports.
- **Responsiveness**: Fully functional on mobile/tablet browsers for field use.

---

## 8. System Architecture & Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5 |
| **Backend** | Python 3, Django 5.x |
| **Database** | PostgreSQL (Supabase) with SQLite fallback |
| **Security** | Django Auth + Supabase RLS |
| **Reporting** | Openpyxl (Excel) & ReportLab (PDF) |

---

## 9. Success Metrics
- **Centralization**: 100% of field records stored in the portal rather than local sheets.
- **Security Compliance**: Zero unauthorized cross-role or cross-field data access.
- **User Efficiency**: Average time to generate a monthly report reduced from 4 hours to under 2 minutes.
- **Traceability**: 100% of record modifications traceable to a specific user and timestamp via audit logs.

---

**End of Document**
