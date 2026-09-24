"""
Seeds the platform-default roles and permissions so local dev / a fresh
school onboarding doesn't start from an empty RBAC table. Idempotent --
safe to re-run.

Usage: python manage.py seed_rbac
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role, RolePermission

PLATFORM_ROLES = [
    "Super Admin",
    "School Admin",
    "Principal",
    "Accountant",
    "Procurement Officer",
    "Department Head",
    "Teacher",
    "Auditor",
    "Parent",
]

# Grows as each module ships (Phase 3 adds fees.*, Phase 4 adds expenses.*,
# etc). Kept here rather than a migration so it's easy to extend without a
# new migration every time a permission is added.
PERMISSIONS = [
    ("schools.view_departments", "View departments"),
    ("schools.manage_departments", "Create/edit/delete departments"),
    ("schools.view_academic_years", "View academic years and terms"),
    ("schools.manage_academic_years", "Create/edit/delete academic years and terms"),
    ("schools.view_classes", "View classes"),
    ("schools.manage_classes", "Create/edit/delete classes"),
    ("students.view_students", "View students"),
    ("students.manage_students", "Create/edit/delete students"),
    ("students.view_parents", "View parents"),
    ("students.manage_parents", "Create/edit/delete parents"),
    ("fees.view_invoices", "View fee structures, invoices, payments, receipts"),
    ("fees.manage_fee_structures", "Create/edit fee categories and fee structures"),
    ("fees.manage_invoices", "Create invoices"),
    ("fees.record_payments", "Record payments against invoices"),
    ("fees.reverse_payments", "Reverse a previously recorded payment"),
    ("suppliers.view_suppliers", "View suppliers"),
    ("suppliers.manage_suppliers", "Create/edit/delete suppliers"),
    ("expenses.view_expenses", "View expense requests"),
    ("expenses.create_expenses", "Create, submit, and cancel expense requests"),
    ("expenses.approve_expenses", "Approve or reject expense requests"),
    ("expenses.record_expense_payment", "Mark an approved expense as paid"),
    ("procurement.view_procurement", "View purchase requests, quotations, purchase orders, deliveries, invoices"),
    ("procurement.create_purchase_requests", "Create, submit, and cancel purchase requests"),
    ("procurement.approve_purchase_requests", "Approve or reject purchase requests"),
    ("procurement.manage_quotations", "Submit supplier quotations against an approved purchase request"),
    ("procurement.issue_purchase_orders", "Issue a purchase order from an approved request + selected quotation"),
    ("procurement.record_deliveries", "Record delivery against a purchase order"),
    ("procurement.record_supplier_invoices", "Record a supplier's invoice against a purchase order"),
    ("audit.view_audit_logs", "View the audit log"),
    ("budgets.view_budgets", "View budgets and utilization"),
    ("budgets.manage_budgets", "Create/edit budgets"),
    ("dashboard.view_dashboard", "View the financial dashboard and control center alerts"),
    ("ai.use_assistant", "Ask the AI financial assistant questions"),
]

# role_name -> list of permission codenames. Principal and Auditor get
# read access to everything by convention; write access is granted
# module-by-module as each is built.
ROLE_PERMISSIONS = {
    "School Admin": [
        "schools.view_departments", "schools.manage_departments",
        "schools.view_academic_years", "schools.manage_academic_years",
        "schools.view_classes", "schools.manage_classes",
        "students.view_students", "students.manage_students",
        "students.view_parents", "students.manage_parents",
        "fees.view_invoices", "fees.manage_fee_structures",
        "fees.manage_invoices", "fees.record_payments", "fees.reverse_payments",
        "suppliers.view_suppliers", "suppliers.manage_suppliers",
        "expenses.view_expenses", "expenses.create_expenses",
        "expenses.approve_expenses", "expenses.record_expense_payment",
        "procurement.view_procurement", "procurement.create_purchase_requests",
        "procurement.approve_purchase_requests", "procurement.manage_quotations",
        "procurement.issue_purchase_orders", "procurement.record_deliveries",
        "procurement.record_supplier_invoices",
        "audit.view_audit_logs", "budgets.view_budgets", "budgets.manage_budgets",
        "dashboard.view_dashboard", "ai.use_assistant",
    ],
    "Principal": [
        "schools.view_departments", "schools.view_academic_years",
        "schools.view_classes", "students.view_students", "students.view_parents",
        "fees.view_invoices", "fees.reverse_payments",
        "suppliers.view_suppliers",
        "expenses.view_expenses", "expenses.approve_expenses",
        "procurement.view_procurement", "procurement.approve_purchase_requests",
        "audit.view_audit_logs", "budgets.view_budgets",
        "dashboard.view_dashboard", "ai.use_assistant",
    ],
    "Accountant": [
        "schools.view_departments",
        "fees.view_invoices", "fees.manage_fee_structures",
        "fees.manage_invoices", "fees.record_payments",
        # Deliberately no fees.reverse_payments: separation of duties --
        # whoever records a payment shouldn't unilaterally be able to
        # un-record it. See PaymentViewSet.reverse().
        "students.view_students", "students.view_parents",
        "suppliers.view_suppliers", "suppliers.manage_suppliers",
        "expenses.view_expenses", "expenses.create_expenses",
        "expenses.record_expense_payment",
        # No expenses.approve_expenses: the same separation-of-duties
        # logic applies here -- an Accountant can request and pay out
        # expenses but not approve them (including their own, which is
        # also blocked unconditionally in services.py regardless of role).
        "procurement.view_procurement", "procurement.record_supplier_invoices",
        "budgets.view_budgets", "ai.use_assistant",
    ],
    "Department Head": [
        "schools.view_departments", "students.view_students",
        "expenses.view_expenses", "expenses.create_expenses",
        "procurement.view_procurement", "procurement.create_purchase_requests",
    ],
    "Procurement Officer": [
        "schools.view_departments",
        "suppliers.view_suppliers", "suppliers.manage_suppliers",
        "expenses.view_expenses",
        "procurement.view_procurement", "procurement.create_purchase_requests",
        "procurement.manage_quotations", "procurement.issue_purchase_orders",
        "procurement.record_deliveries", "procurement.record_supplier_invoices",
        # No procurement.approve_purchase_requests: the Officer runs the
        # pipeline day-to-day but approval authority sits with Principal/
        # Admin -- same separation-of-duties shape as everywhere else.
    ],
    "Teacher": ["students.view_students"],
    "Auditor": [
        "schools.view_departments", "schools.view_academic_years",
        "schools.view_classes", "students.view_students", "students.view_parents",
        "fees.view_invoices", "suppliers.view_suppliers", "expenses.view_expenses",
        "procurement.view_procurement", "audit.view_audit_logs", "budgets.view_budgets",
        "dashboard.view_dashboard",
    ],
}


class Command(BaseCommand):
    help = "Seed platform-default roles and permissions (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        for codename, description in PERMISSIONS:
            _, created = Permission.objects.get_or_create(
                codename=codename, defaults={"description": description}
            )
            self.stdout.write(f"{'created' if created else 'exists '} permission: {codename}")

        for name in PLATFORM_ROLES:
            _, created = Role.objects.get_or_create(name=name, school=None)
            self.stdout.write(f"{'created' if created else 'exists '} role: {name}")

        for role_name, codenames in ROLE_PERMISSIONS.items():
            role = Role.objects.get(name=role_name, school=None)
            for codename in codenames:
                perm = Permission.objects.get(codename=codename)
                RolePermission.objects.get_or_create(role=role, permission=perm)

        self.stdout.write(self.style.SUCCESS("RBAC seed complete."))
