"""
Servicio de Aprovisionamiento Seguro e Idempotente de Tenants (ADR-002 y ADR-005).
Administra la creación de bases de datos PostgreSQL y la segregación física del filestore
sin exponer el socket de Docker a la aplicación web.
"""
import os
import re
import shutil
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class ProvisioningError(Exception):
    pass


class ProvisioningService:
    @staticmethod
    def sanitize_database_name(slug: str) -> str:
        """
        Genera y sanitiza el nombre físico de la base de datos PostgreSQL:
        sofia_tenant_<slug_sanitizado>
        Previene vulnerabilidades de inyección SQL en sentencias DDL.
        """
        clean_slug = re.sub(r"[^a-z0-9_]", "_", slug.strip().lower())
        # Limitar longitud máxima de identificador PostgreSQL (63 bytes)
        db_name = f"sofia_tenant_{clean_slug}"[:63]
        return db_name

    @classmethod
    def get_filestore_path(cls, base_dir: str, slug: str, db_name: str) -> str:
        """Construye la ruta del directorio segregado del filestore."""
        return os.path.join(base_dir, slug, "filestore", db_name)

    @classmethod
    def create_tenant_database(
        cls,
        db_name: str,
        owner_user: str = "odoo_runtime_user",
        pg_host: str = "postgres",
        pg_port: int = 5432,
        admin_user: str = "sofia_admin",
        admin_password: str = "sofia_pass",
        max_connections: int = 30,
    ) -> bool:
        """
        Ejecuta la sentencia DDL para crear la base de datos del tenant de forma aislada
        y configura el límite máximo de conexiones concurrentes para evitar el problema del vecino ruidoso.
        """
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user=admin_user,
                password=admin_password,
                host=pg_host,
                port=pg_port,
                connect_timeout=10,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Comprobar existencia
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return False  # Ya existía

            # Verificar si existe el rol owner_user; si no, usar admin_user
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (owner_user,))
            actual_owner = owner_user if cursor.fetchone() else admin_user

            # Comprobar si existe la plantilla de oro sofia_template_db (con Odoo y es_PE pre-instalados)
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'sofia_template_db'")
            has_template = cursor.fetchone()

            if has_template:
                # Terminar conexiones inactivas al template para permitir clonado seguro
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = 'sofia_template_db' AND pid <> pg_backend_pid();
                """)
                cursor.execute(f'CREATE DATABASE "{db_name}" OWNER "{actual_owner}" TEMPLATE "sofia_template_db";')
            else:
                cursor.execute(f'CREATE DATABASE "{db_name}" OWNER "{actual_owner}";')
            
            # Limitar conexiones máximas permitidas para esta base de datos
            cursor.execute(f'ALTER DATABASE "{db_name}" WITH CONNECTION LIMIT {max_connections};')

            cursor.close()
            conn.close()
            return True

        except Exception as e:
            raise ProvisioningError(f"Error al crear base de datos '{db_name}': {str(e)}")

    @classmethod
    def initialize_filestore(cls, filestore_path: str, mode: int = 0o750) -> bool:
        """
        Crea el árbol de directorios para el filestore físico del tenant
        aplicando permisos restrictivos (0750) para impedir lectura por otros usuarios.
        """
        try:
            os.makedirs(filestore_path, exist_ok=True)
            try:
                os.chmod(filestore_path, mode)
            except (AttributeError, OSError):
                # En sistemas de archivos Windows / NTFS se ignora el chmod POSIX
                pass
            return True
        except Exception as e:
            raise ProvisioningError(f"Error al inicializar filestore en '{filestore_path}': {str(e)}")

    @classmethod
    def drop_tenant_database(
        cls,
        db_name: str,
        pg_host: str = "postgres",
        pg_port: int = 5432,
        admin_user: str = "sofia_admin",
        admin_password: str = "sofia_pass",
    ) -> bool:
        """
        Termina conexiones activas y elimina la base de datos de un tenant (para rollback o desaprovisionamiento).
        """
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user=admin_user,
                password=admin_password,
                host=pg_host,
                port=pg_port,
                connect_timeout=10,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Desconectar sesiones activas de esa base de datos
            cursor.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                  AND pid <> pg_backend_pid();
                """,
                (db_name,),
            )

            # Eliminar base de datos
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}";')

            cursor.close()
            conn.close()
            return True
        except Exception as e:
            raise ProvisioningError(f"Error al eliminar base de datos '{db_name}': {str(e)}")

    @classmethod
    def provision_tenant_pipeline(
        cls,
        slug: str,
        base_filestore_dir: str = "/var/lib/sofia/filestores",
        pg_host: str = "postgres",
        pg_port: int = 5432,
        admin_user: str = "sofia_admin",
        admin_password: str = "sofia_pass",
        owner_user: str = "odoo_runtime_user",
        max_connections: int = 30,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo y atómico de aprovisionamiento de un tenant:
        1. Sanitización de identificador.
        2. Creación de base de datos PostgreSQL con límite de conexiones.
        3. Creación de filestore aislado con permisos 0750.
        4. Si falla en algún punto, realiza rollback ordenado.
        """
        db_name = cls.sanitize_database_name(slug)
        filestore_path = cls.get_filestore_path(base_filestore_dir, slug, db_name)

        if dry_run:
            return {
                "status": "DRY_RUN_SUCCESS",
                "slug": slug,
                "database_name": db_name,
                "filestore_path": filestore_path,
                "max_connections": max_connections,
            }

        db_created = False
        try:
            # 1. Crear Base de Datos
            db_created = cls.create_tenant_database(
                db_name=db_name,
                owner_user=owner_user,
                pg_host=pg_host,
                pg_port=pg_port,
                admin_user=admin_user,
                admin_password=admin_password,
                max_connections=max_connections,
            )

            # 2. Inicializar Filestore
            cls.initialize_filestore(filestore_path)

            return {
                "status": "PROVISIONED",
                "slug": slug,
                "database_name": db_name,
                "filestore_path": filestore_path,
                "new_database": db_created,
            }

        except Exception as e:
            # Rollback si ocurrió un error tras crear la base de datos
            if db_created:
                try:
                    cls.drop_tenant_database(
                        db_name=db_name,
                        pg_host=pg_host,
                        pg_port=pg_port,
                        admin_user=admin_user,
                        admin_password=admin_password,
                    )
                except Exception:
                    pass
            # Limpiar directorio de filestore parcial
            if os.path.exists(filestore_path):
                shutil.rmtree(filestore_path, ignore_errors=True)

            raise ProvisioningError(f"Pipeline de aprovisionamiento falló para '{slug}': {str(e)}")
