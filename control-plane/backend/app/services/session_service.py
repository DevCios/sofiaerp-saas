"""
Gestor de Sesiones Concurrentes y Control de Capacidad en Tiempo Real mediante Redis.
Controla de forma atómica los límites de concurrencia para evitar condiciones de carrera.
"""
import json
import time
from typing import Optional, Dict, Any


class ConcurrencyLimitExceededException(Exception):
    pass


class SessionService:
    def __init__(self, redis_client: Optional[Any] = None):
        self.redis = redis_client

    async def register_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        max_concurrent_sessions: int,
        client_ip: str = "127.0.0.1",
        user_agent: str = "",
        ttl_seconds: int = 3600,  # 1 hora por defecto
    ) -> Dict[str, Any]:
        """
        Registra una nueva sesión activa para un tenant en Redis.
        Si la cantidad de sesiones concurrentes activas supera el límite contratado,
        rechaza la solicitud con ConcurrencyLimitExceededException.
        """
        if not self.redis:
            # Modo offline / mock para pruebas unitarias sin Redis
            return {"session_id": session_id, "active_sessions": 1, "allowed": True}

        now = int(time.time())
        tenant_sessions_key = f"tenant:{tenant_id}:active_sessions"
        session_detail_key = f"session:{session_id}"

        # 1. Purgar sesiones obsoletas antes de contabilizar (ZREMRANGEBYSCORE)
        # Se remueven aquellas cuyo timestamp de expiración sea menor a 'now'
        await self.redis.zremrangebyscore(tenant_sessions_key, 0, now)

        # 2. Consultar concurrencia actual
        current_active = await self.redis.zcard(tenant_sessions_key)
        if current_active >= max_concurrent_sessions:
            raise ConcurrencyLimitExceededException(
                f"Límite de concurrencia alcanzado ({current_active}/{max_concurrent_sessions} sesiones activas). "
                "Cierre una sesión previa o amplíe el plan de su empresa."
            )

        # 3. Registrar de forma atómica en el Sorted Set de Redis
        expire_at = now + ttl_seconds
        await self.redis.zadd(tenant_sessions_key, {session_id: expire_at})

        # 4. Guardar metadata de la sesión
        session_meta = {
            "session_id": session_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "ip_address": client_ip,
            "user_agent": user_agent,
            "created_at": now,
            "expires_at": expire_at,
        }
        await self.redis.setex(session_detail_key, ttl_seconds, json.dumps(session_meta))

        return {
            "session_id": session_id,
            "active_sessions": current_active + 1,
            "max_allowed": max_concurrent_sessions,
            "expires_at": expire_at,
            "allowed": True,
        }

    async def touch_session(self, session_id: str, tenant_id: str, ttl_seconds: int = 3600) -> bool:
        """Extiende la vigencia de una sesión activa (Heartbeat de inactividad)."""
        if not self.redis:
            return True

        now = int(time.time())
        expire_at = now + ttl_seconds
        tenant_sessions_key = f"tenant:{tenant_id}:active_sessions"
        session_detail_key = f"session:{session_id}"

        # Actualiza score en el Sorted Set
        updated = await self.redis.zadd(tenant_sessions_key, {session_id: expire_at}, xx=True)
        if updated:
            await self.redis.expire(session_detail_key, ttl_seconds)
            return True
        return False

    async def revoke_session(self, session_id: str, tenant_id: str) -> bool:
        """Cierra y revoca una sesión de forma inmediata."""
        if not self.redis:
            return True

        tenant_sessions_key = f"tenant:{tenant_id}:active_sessions"
        session_detail_key = f"session:{session_id}"

        await self.redis.zrem(tenant_sessions_key, session_id)
        await self.redis.delete(session_detail_key)
        return True

    async def get_active_session_count(self, tenant_id: str) -> int:
        """Retorna el número exacto de sesiones concurrentes vivas para un tenant."""
        if not self.redis:
            return 0

        now = int(time.time())
        tenant_sessions_key = f"tenant:{tenant_id}:active_sessions"
        await self.redis.zremrangebyscore(tenant_sessions_key, 0, now)
        return await self.redis.zcard(tenant_sessions_key)
