def migrate(cr, version):
    # IAP provider was removed: fall back to SUNAT for companies still set to it.
    cr.execute(
        "UPDATE res_company SET l10n_pe_edi_provider = 'sunat' WHERE l10n_pe_edi_provider = 'iap'"
    )
