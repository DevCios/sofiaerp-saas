"""
Servicio de Gestión de Versiones de Runtime, Migration Lab y Dedicated Runtimes (Sección 16 y 7.1).
Permite evaluar compatibilidad de versiones, clonar bases a un entorno de pruebas aislado (Migration Lab)
y generar configuraciones para migración de Shared Protected a Dedicated Runtime sin pérdida de datos.
"""
import os
import re
from typing import Dict, Any, List, Optional


class MigrationService:
    SUPPORTED_VERSIONS = ["18.0", "19.0", "20.0"]

    @classmethod
    def check_version_compatibility(cls, current_version: str, target_version: str) -> Dict[str, Any]:
        """
        Verifica si la ruta de actualización entre versiones es válida y no destructiva.
        No permite downgrades directos ni saltos entre versiones no soportadas.
        """
        if target_version not in cls.SUPPORTED_VERSIONS:
            return {
                "compatible": False,
                "reason": f"La versión destino '{target_version}' no está certificada en el Version Registry de SOFIA.",
            }

        curr_major = float(current_version)
        target_major = float(target_version)

        if target_major < curr_major:
            return {
                "compatible": False,
                "reason": f"Downgrade no permitido de v{current_version} a v{target_version}. Los esquemas Odoo no son retrocompatibles.",
            }

        if target_major == curr_major:
            return {
                "compatible": True,
                "upgrade_type": "MINOR_PATCH",
                "risk_level": "LOW",
                "requires_lab": False,
            }

        return {
            "compatible": True,
            "upgrade_type": "MAJOR_UPGRADE",
            "risk_level": "HIGH",
            "requires_lab": True,
            "steps": [
                "1. Snapshot pre-migración completo (PostgreSQL + Filestore)",
                "2. Clonación a base de datos de laboratorio (Migration Lab)",
                "3. Ejecución de migración de esquema en entorno aislado (-u all)",
                "4. Validación de integridad de datos y módulos SUNAT/GRE",
                "5. Aprobación y aplicación en ventana de mantenimiento",
            ],
        }

    @classmethod
    def generate_migration_lab_sql(cls, production_db: str, staging_db: str, owner_user: str = "odoo_runtime_user") -> list:
        """
        Genera las sentencias SQL seguras para clonar la base de datos productiva
        hacia el Migration Lab utilizando la directiva TEMPLATE de PostgreSQL.
        """
        clean_prod = re.sub(r"[^a-z0-9_]", "", production_db)
        clean_staging = re.sub(r"[^a-z0-9_]", "", staging_db)

        return [
            # Desconectar temporalmente sesiones si es necesario o clonar directamente
            f'CREATE DATABASE "{clean_staging}" WITH TEMPLATE "{clean_prod}" OWNER "{owner_user}";',
        ]

    @classmethod
    def generate_dedicated_runtime_config(
        cls,
        tenant_slug: str,
        database_name: str,
        filestore_path: str,
        allocated_cpu: str = "2.0",
        allocated_memory: str = "4g",
        exposed_port: int = 8070,
    ) -> Dict[str, Any]:
        """
        Genera la configuración técnica para trasladar un cliente de Shared Protected
        hacia un Dedicated Runtime (Contenedor Odoo exclusivo con límites cgroups).
        El cliente conserva exactamente la misma identidad, base de datos, filestore y dominios.
        """
        service_name = f"odoo-dedicated-{tenant_slug}"

        compose_snippet = {
            "services": {
                service_name: {
                    "image": "odoo:20.0",
                    "container_name": f"sofia-{service_name}",
                    "restart": "unless-stopped",
                    "deploy": {
                        "resources": {
                            "limits": {
                                "cpus": allocated_cpu,
                                "memory": allocated_memory,
                            }
                        }
                    },
                    "environment": {
                        "HOST": "pgbouncer",
                        "PORT": 6432,
                        "USER": "odoo_runtime_user",
                    },
                    "volumes": [
                        f"{filestore_path}:/var/lib/odoo",
                        "./odoo/odoo.conf:/etc/odoo/odoo.conf:ro",
                        "../../control-plane/keys:/etc/sofia/keys:ro",
                        "../../products/sofia-erp/addons:/mnt/extra-addons:ro",
                    ],
                    "networks": ["sofia-net-app", "sofia-net-data"],
                }
            }
        }

        nginx_upstream = f"upstream odoo_dedicated_{tenant_slug} {{\n    server {service_name}:8069;\n}}\n"

        return {
            "tenant_slug": tenant_slug,
            "mode": "DEDICATED",
            "service_name": service_name,
            "compose_snippet": compose_snippet,
            "nginx_upstream_block": nginx_upstream,
            "database_name": database_name,
            "filestore_path": filestore_path,
        }
