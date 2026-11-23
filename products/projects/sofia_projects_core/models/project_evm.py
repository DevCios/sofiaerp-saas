# -*- coding: utf-8 -*-
"""
SOFIA Projects Core — Control de Valor Ganado (EVM), Índices SPI/CPI y Rentabilidad en Tiempo Real.
"""
from odoo import models, fields, api, _


class SofiaProjectEVM(models.Model):
    _inherit = 'project.project'

    planned_value = fields.Monetary(
        string='Valor Planificado (PV)',
        help='Presupuesto autorizado para el trabajo planificado a la fecha',
    )
    earned_value = fields.Monetary(
        string='Valor Ganado (EV)',
        compute='_compute_evm_metrics',
        store=True,
        help='Valor del trabajo físicamente completado expresado en términos del presupuesto original',
    )
    actual_cost = fields.Monetary(
        string='Costo Real Ejecutado (AC)',
        compute='_compute_evm_metrics',
        store=True,
        help='Costo real total incurrido en la ejecución de las actividades del proyecto',
    )

    cost_variance = fields.Monetary(
        string='Variación del Costo (CV = EV - AC)',
        compute='_compute_evm_metrics',
        store=True,
    )
    schedule_variance = fields.Monetary(
        string='Variación del Cronograma (SV = EV - PV)',
        compute='_compute_evm_metrics',
        store=True,
    )

    cpi = fields.Float(
        string='Índice de Rendimiento del Costo (CPI)',
        compute='_compute_evm_metrics',
        store=True,
        digits=(12, 2),
        help='Medida de la eficiencia del costo. > 1.0 indica costo por debajo del presupuesto.',
    )
    spi = fields.Float(
        string='Índice de Rendimiento del Cronograma (SPI)',
        compute='_compute_evm_metrics',
        store=True,
        digits=(12, 2),
        help='Medida de la eficiencia del cronograma. > 1.0 indica avance por delante de lo programado.',
    )

    @api.depends('planned_value', 'task_ids.stage_id', 'task_ids.timesheet_ids.unit_amount')
    def _compute_evm_metrics(self):
        for project in self:
            total_tasks = len(project.task_ids)
            completed_tasks = len(project.task_ids.filtered(lambda t: t.stage_id.fold or t.stage_id.name == 'Hecho'))
            completion_rate = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0

            ev = project.planned_value * completion_rate
            # Costo real acumulado por partes de horas
            ac = sum(project.task_ids.mapped('timesheet_ids.unit_amount')) * 50.0  # Tarifa estándar HH

            project.earned_value = ev
            project.actual_cost = ac
            project.cost_variance = ev - ac
            project.schedule_variance = ev - project.planned_value

            project.cpi = (ev / ac) if ac > 0 else 1.0
            project.spi = (ev / project.planned_value) if project.planned_value > 0 else 1.0
