FROM odoo:20.0

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-jwt python3-cryptography || \
    pip3 install --no-cache-dir --break-system-packages pyjwt cryptography mercadopago && \
    rm -rf /var/lib/apt/lists/*

USER odoo
