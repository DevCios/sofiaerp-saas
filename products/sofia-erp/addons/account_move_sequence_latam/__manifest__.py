{
    "name": "Olitech - Account Move Number Sequence Latam",
    "version": "20.0.1.1.0",
    "category": "Accounting",
    "license": "GPL-3",
    "summary": "Generate journal entry number from sequence",
    "author": "HFoc",
    "maintainers": ["HFoc"],
    "website": "https://olitech.dev",
    "depends": [
        "account","l10n_latam_invoice_document","l10n_pe_edi"
    ],
    "data": [
        "security/ir.access.csv",
        "views/account_journal_views.xml",
        "views/l10n_latam_document_type.xml",
    ],
    "installable": True,
}
