"""Synthetic enterprise document corpus.

Every document is fictional, written for this project, and set in a generic
company ("Northwind Traders"). Documents carry per-document ACL metadata —
the same shape an enterprise connector (SharePoint, Confluence, Drive) would
supply — because retrieval-time permission enforcement is only meaningful if
the index knows who may see what.

The corpus deliberately includes:
* broadly accessible policy docs (normal questions),
* role-restricted docs (salary bands, vendor terms) for ACL tests,
* a restricted directory containing synthetic PII, used to prove that PII is
  redacted from output even for roles allowed to retrieve it.
"""

from __future__ import annotations

from .schemas import Document, Role

ALL = [Role.EMPLOYEE, Role.MANAGER, Role.HR, Role.FINANCE, Role.ADMIN]


def synthetic_corpus() -> list[Document]:
    return [
        Document(
            doc_id="doc-handbook",
            title="Employee Handbook 2026",
            department="People",
            classification="internal",
            allowed_roles=ALL,
            text=(
                "Northwind Traders employees accrue paid time off based on tenure. "
                "Employees with less than three years of service receive 15 days of paid time off per year. "
                "Employees with three to seven years of service receive 20 days of paid time off per year. "
                "Employees with more than seven years of service receive 25 days of paid time off per year. "
                "Unused paid time off may be carried over up to a maximum of five days into the next calendar year. "
                "Employees may work remotely up to two days per week with manager approval. "
                "Remote work days must be recorded in the time tracking system. "
                "The standard work week is forty hours, Monday through Friday."
            ),
        ),
        Document(
            doc_id="doc-security",
            title="IT Security Policy",
            department="IT",
            classification="internal",
            allowed_roles=ALL,
            text=(
                "All employees must use multi-factor authentication for company systems. "
                "Passwords must be at least fourteen characters and must not be reused across systems. "
                "Suspected phishing emails must be reported to the security team within one business day. "
                "Company data must never be stored on personal devices or personal cloud accounts. "
                "Security incidents are triaged by severity, and critical incidents require notification within one hour. "
                "Laptops must have full disk encryption enabled at all times."
            ),
        ),
        Document(
            doc_id="doc-travel",
            title="Travel and Expense Policy",
            department="Finance",
            classification="internal",
            allowed_roles=ALL,
            text=(
                "Employees traveling on company business may book economy class flights for trips under six hours. "
                "Business class is permitted for flights longer than six hours with director approval. "
                "Hotel expenses are reimbursed up to two hundred twenty dollars per night in most cities. "
                "Meals are reimbursed up to seventy five dollars per day with itemized receipts. "
                "Expense reports must be submitted within thirty days of travel. "
                "Personal expenses and minibar charges are not reimbursable."
            ),
        ),
        Document(
            doc_id="doc-oncall",
            title="Engineering On-Call Guide",
            department="Engineering",
            classification="internal",
            allowed_roles=[Role.EMPLOYEE, Role.MANAGER, Role.ADMIN],
            text=(
                "The on-call engineer is responsible for acknowledging production alerts within fifteen minutes. "
                "On-call rotations last one week and are scheduled at least four weeks in advance. "
                "On-call engineers receive a stipend of three hundred dollars per week of rotation. "
                "If an incident lasts longer than four hours, the secondary on-call engineer must be paged. "
                "Post-incident reviews are required for all severity one incidents within three business days. "
                "On-call handovers happen every Monday at ten in the morning."
            ),
        ),
        Document(
            doc_id="doc-salary-bands",
            title="Compensation Bands 2026",
            department="People",
            classification="restricted",
            allowed_roles=[Role.HR, Role.ADMIN],
            text=(
                "Senior engineer compensation band for 2026 is one hundred sixty thousand to two hundred ten thousand dollars base salary. "
                "Engineering manager compensation band for 2026 is one hundred ninety thousand to two hundred fifty thousand dollars base salary. "
                "Director compensation band for 2026 is two hundred forty thousand to three hundred twenty thousand dollars base salary. "
                "Annual bonuses target ten to twenty five percent of base salary depending on level. "
                "Compensation bands are reviewed every year in the fourth quarter and are confidential."
            ),
        ),
        Document(
            doc_id="doc-directory",
            title="Internal Contact Directory (Restricted)",
            department="People",
            classification="restricted",
            allowed_roles=[Role.HR, Role.ADMIN],
            text=(
                "Restricted internal directory for HR use only. "
                "Priya Natarajan, recruiting coordinator, email priya.natarajan@example.com, phone 415-555-0134, employee ID 8841-22-1098. "
                "Marcus Webb, payroll specialist, email marcus.webb@example.com, phone 415-555-0177, employee ID 7741-09-5523. "
                "Elena Petrova, benefits analyst, email elena.petrova@example.com, phone 415-555-0119, employee ID 9021-44-7810. "
                "This directory contains personal contact data and must not be shared outside the People team."
            ),
        ),
        Document(
            doc_id="doc-roadmap",
            title="Product Roadmap FY27",
            department="Product",
            classification="confidential",
            allowed_roles=[Role.MANAGER, Role.HR, Role.ADMIN],
            text=(
                "The FY27 product roadmap focuses on three themes: platform reliability, self-serve analytics, and international expansion. "
                "The self-serve analytics launch is planned for the second quarter. "
                "International expansion begins with the European market in the third quarter. "
                "Platform reliability targets ninety nine point nine five percent availability by the end of the fiscal year. "
                "Roadmap details are confidential and must not be shared externally."
            ),
        ),
        Document(
            doc_id="doc-vendor",
            title="Vendor Contract Summary",
            department="Finance",
            classification="confidential",
            allowed_roles=[Role.FINANCE, Role.MANAGER, Role.ADMIN],
            text=(
                "The cloud infrastructure vendor agreement renews on March first with a three year term. "
                "The agreement includes a committed spend of one point two million dollars per year. "
                "Early termination requires twelve months written notice and a termination fee. "
                "The customer data platform contract expires in June and renewal negotiations begin in April. "
                "Vendor pricing terms are confidential and must not be disclosed to other vendors."
            ),
        ),
    ]
