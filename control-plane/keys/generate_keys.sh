#!/bin/bash
# ==============================================================================
# SOFIA ERP — Generador de Claves Asimétricas RSA para OIDC / JWKS (ADR-004)
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "Generando par de claves RSA 4096-bit en: $DIR"
openssl genpkey -algorithm RSA -out "$DIR/jwt_private.pem" -pkeyopt rsa_keygen_bits:4096
openssl rsa -pubout -in "$DIR/jwt_private.pem" -out "$DIR/jwt_public.pem"

chmod 600 "$DIR/jwt_private.pem"
chmod 644 "$DIR/jwt_public.pem"

echo "Claves generadas exitosamente."
