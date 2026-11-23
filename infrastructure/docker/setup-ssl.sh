#!/bin/bash
# ==============================================================================
# SOFIA ERP — Script de Automatización SSL Let's Encrypt (HTTPS Seguro)
# ==============================================================================
set -e

echo ">>> 1. Instalando Certbot en el servidor..."
apt-get update && apt-get install -y certbot

echo ">>> 2. Deteniendo Nginx temporalmente para liberar puertos 80/443..."
docker compose stop edge-router

echo ">>> 3. Emitiendo certificado SSL oficial Let's Encrypt..."
certbot certonly --standalone \
  -d sofiaerp.com \
  -d www.sofiaerp.com \
  -d api.sofiaerp.com \
  -d avantgarde.sofiaerp.com \
  --agree-tos \
  -m lpalacioslapa@gmail.com \
  --non-interactive

echo ">>> 4. Habilitando configuración HTTPS en Nginx..."
cp nginx/conf.d/default-ssl.conf nginx/conf.d/default.conf

echo ">>> 5. Levantando Nginx con HTTPS cifrado..."
docker compose up -d edge-router

echo "=========================================================================="
echo ">>> ¡ENHORABUENA! HTTPS ACTIVADO CON ÉXITO CON CANDADO DE SEGURIDAD <<<"
echo "Sitios seguros disponibles:"
echo " • https://api.sofiaerp.com/admin"
echo " • https://avantgarde.sofiaerp.com"
echo " • https://sofiaerp.com"
echo "=========================================================================="
