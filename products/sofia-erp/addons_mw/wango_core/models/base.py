from odoo import models, fields
import uuid


class WangoBaseMixin(models.AbstractModel):
    _name = 'wango.base.mixin'
    _description = 'WanGO Base Mixin'

    uuid = fields.Char(
        string='UUID',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: str(uuid.uuid4())
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
