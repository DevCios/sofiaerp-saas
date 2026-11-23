# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    sofia_user_id = fields.Char(
        string='SOFIA Global User ID',
        index=True,
        help='Identificador único global del usuario en el Control Plane de SOFIA Platform',
        copy=False,
    )
    sofia_roles = fields.Char(
        string='Roles SOFIA Platform',
        help='Roles asignados en el Control Plane (ej. TENANT_ADMIN, OPERATOR)',
        copy=False,
    )
    sofia_last_sync = fields.Datetime(
        string='Última Sincronización SOFIA',
        readonly=True,
    )
