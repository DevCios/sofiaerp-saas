# -*- coding: utf-8 -*-

from odoo import models, fields

class WangoProvince(models.Model):
    _name = 'wango.province'
    _description = 'Provincia de Perú'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código UBIGEO / Ref')
    state_id = fields.Many2one('res.country.state', string='Departamento', required=True, domain="[('country_id.code', '=', 'PE')]")

    def init(self):
        super(WangoProvince, self).init()
        # Limpieza de provincias duplicadas (mismo nombre y departamento)
        self.env.cr.execute("""
            DO $$
            DECLARE
                r RECORD;
                kept_id INTEGER;
                dup_ids INTEGER[];
            BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wango_province') THEN
                    FOR r IN 
                        SELECT name, state_id, COUNT(*), MIN(id) as min_id
                        FROM wango_province
                        GROUP BY name, state_id
                        HAVING COUNT(*) > 1
                    LOOP
                        kept_id := r.min_id;
                        
                        SELECT array_agg(id) INTO dup_ids
                        FROM wango_province
                        WHERE name = r.name AND state_id = r.state_id AND id != kept_id;
                        
                        -- Actualizar referencias en otras tablas
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wango_district') THEN
                            UPDATE wango_district SET province_id = kept_id WHERE province_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_store_branch') THEN
                            UPDATE delivery_store_branch SET province_id = kept_id WHERE province_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_coverage') THEN
                            UPDATE delivery_coverage SET province_id = kept_id WHERE province_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_agency_cost') THEN
                            UPDATE delivery_agency_cost SET province_id = kept_id WHERE province_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sale_order') THEN
                            UPDATE sale_order SET delivery_province_id = kept_id WHERE delivery_province_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'product_template') THEN
                            UPDATE product_template SET wango_origin_province_id = kept_id WHERE wango_origin_province_id = ANY(dup_ids);
                        END IF;
                        
                        DELETE FROM wango_province WHERE id = ANY(dup_ids);
                    END LOOP;
                END IF;
            END $$;
        """)

        # Limpieza de distritos duplicados (mismo nombre y provincia)
        self.env.cr.execute("""
            DO $$
            DECLARE
                r RECORD;
                kept_id INTEGER;
                dup_ids INTEGER[];
            BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wango_district') THEN
                    FOR r IN 
                        SELECT name, province_id, COUNT(*), MIN(id) as min_id
                        FROM wango_district
                        GROUP BY name, province_id
                        HAVING COUNT(*) > 1
                    LOOP
                        kept_id := r.min_id;
                        
                        SELECT array_agg(id) INTO dup_ids
                        FROM wango_district
                        WHERE name = r.name AND province_id = r.province_id AND id != kept_id;
                        
                        -- Actualizar referencias
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_store_branch') THEN
                            UPDATE delivery_store_branch SET district_id = kept_id WHERE district_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_coverage') THEN
                            UPDATE delivery_coverage SET district_id = kept_id WHERE district_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delivery_agency_cost') THEN
                            UPDATE delivery_agency_cost SET district_id = kept_id WHERE district_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sale_order') THEN
                            UPDATE sale_order SET delivery_district_id = kept_id WHERE delivery_district_id = ANY(dup_ids);
                        END IF;
                        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'product_template') THEN
                            UPDATE product_template SET wango_origin_district_id = kept_id WHERE wango_origin_district_id = ANY(dup_ids);
                        END IF;
                        
                        DELETE FROM wango_district WHERE id = ANY(dup_ids);
                    END LOOP;
                END IF;
            END $$;
        """)


class WangoDistrict(models.Model):
    _name = 'wango.district'
    _description = 'Distrito de Perú'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código UBIGEO / Ref')
    province_id = fields.Many2one('wango.province', string='Provincia', required=True)
    state_id = fields.Many2one('res.country.state', string='Departamento', related='province_id.state_id', store=True)
