# -*- coding: utf-8 -*-
"""
Hooks consolidados de instalación y desinstalación para l10n_pe_edi_sofia.
Ejecuta en orden:
1. Carga rápida de códigos UNSPSC y asignación a UoMs (product_unspsc).
2. Activación de códigos SUNAT obligatorios y sincronización de impuestos/líneas (l10n_pe_edi).
"""
from .modules.product_unspsc.hooks import (
    post_init_hook as _unspsc_post_init_hook,
    uninstall_hook as _unspsc_uninstall_hook,
)
from .modules.l10n_pe_edi.hooks import post_init_hook as _edi_post_init_hook


def post_init_hook(env):
    _unspsc_post_init_hook(env)
    _edi_post_init_hook(env)


def uninstall_hook(env):
    _unspsc_uninstall_hook(env)
