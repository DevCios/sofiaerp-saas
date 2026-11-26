# -*- coding: utf-8 -*-
import base64
import datetime
import hashlib
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from app.core.config import get_settings

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"

settings = get_settings()


def generate_demo_pfx(ruc: str, business_name: str) -> tuple[bytes, str, str, datetime.datetime]:
    """Genera certificado PKCS#12 (.pfx) autofirmado RSA-2048 válido 1 año para SUNAT Beta."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    org = (business_name or "SOFIA GATEWAY DEMO")[:64]
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PE"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COMMON_NAME, f"{ruc} DEMO SUNAT BETA"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(days=365)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    pwd = "sofia_gateway_beta"
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=f"sunat_demo_{ruc}".encode("utf-8"),
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(pwd.encode("utf-8")),
    )
    return pfx_bytes, pwd, f"CN={ruc} DEMO SUNAT BETA, O={org}, C=PE", expires


def inspect_pfx(pfx_bytes: bytes, password: str) -> tuple[str, datetime.datetime]:
    """Valida que el .pfx y la contraseña abran correctamente y extrae Subject + Fecha de expiración."""
    pwd_bytes = password.encode("utf-8") if password else None
    private_key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, pwd_bytes)
    if private_key is None or cert is None:
        raise ValueError("El archivo .pfx no contiene clave privada y certificado válidos.")
    subject = cert.subject.rfc4514_string()
    expires = cert.not_valid_after_utc
    return subject, expires


def sign_ubl_xml(xml_bytes: bytes, pfx_bytes: bytes, password: str) -> tuple[bytes, str]:
    """
    Firma XML UBL 2.1 con XMLDSig Enveloped Signature (RSA-SHA1, compatible 100% con SUNAT).
    Retorna (signed_xml_bytes, digest_value_b64).
    """
    pwd_bytes = password.encode("utf-8") if password else None
    private_key, cert, _ = pkcs12.load_key_and_certificates(pfx_bytes, pwd_bytes)
    if private_key is None or cert is None:
        raise ValueError("Certificado .pfx inválido o contraseña incorrecta.")

    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(xml_bytes, parser=parser)

    # Buscar o crear ext:ExtensionContent
    ext_contents = root.xpath(".//ext:ExtensionContent", namespaces={"ext": NS_EXT})
    if not ext_contents:
        exts = etree.Element(f"{{{NS_EXT}}}UBLExtensions")
        ext = etree.SubElement(exts, f"{{{NS_EXT}}}UBLExtension")
        ext_content = etree.SubElement(ext, f"{{{NS_EXT}}}ExtensionContent")
        root.insert(0, exts)
    else:
        ext_content = ext_contents[-1]
        ext_content.clear()

    # 1. Calcular DigestValue (SHA-1 sobre documento canonizado C14N sin firma)
    c14n_doc = etree.tostring(root, method="c14n", exclusive=False, with_comments=False)
    digest_value = base64.b64encode(hashlib.sha1(c14n_doc).digest()).decode("ascii")

    # 2. Construir nodo ds:Signature
    sig_el = etree.SubElement(ext_content, f"{{{NS_DS}}}Signature", Id="SignatureSOFIA")
    signed_info = etree.SubElement(sig_el, f"{{{NS_DS}}}SignedInfo")
    etree.SubElement(
        signed_info,
        f"{{{NS_DS}}}CanonicalizationMethod",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    etree.SubElement(
        signed_info,
        f"{{{NS_DS}}}SignatureMethod",
        Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1",
    )
    ref = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", URI="")
    transforms = etree.SubElement(ref, f"{{{NS_DS}}}Transforms")
    etree.SubElement(
        transforms,
        f"{{{NS_DS}}}Transform",
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    etree.SubElement(
        ref,
        f"{{{NS_DS}}}DigestMethod",
        Algorithm="http://www.w3.org/2000/09/xmldsig#sha1",
    )
    dv_el = etree.SubElement(ref, f"{{{NS_DS}}}DigestValue")
    dv_el.text = digest_value

    # 3. Firmar SignedInfo canonizado con clave privada RSA
    c14n_signed_info = etree.tostring(signed_info, method="c14n", exclusive=False, with_comments=False)
    raw_sig = private_key.sign(c14n_signed_info, padding.PKCS1v15(), hashes.SHA1())
    sig_val = etree.SubElement(sig_el, f"{{{NS_DS}}}SignatureValue")
    sig_val.text = base64.b64encode(raw_sig).decode("ascii")

    # 4. Adjuntar X509Certificate en DER base64
    key_info = etree.SubElement(sig_el, f"{{{NS_DS}}}KeyInfo")
    x509_data = etree.SubElement(key_info, f"{{{NS_DS}}}X509Data")
    x509_cert = etree.SubElement(x509_data, f"{{{NS_DS}}}X509Certificate")
    x509_cert.text = base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode("ascii")

    signed_bytes = etree.tostring(root, xml_declaration=True, encoding="ISO-8859-1", pretty_print=False)
    return signed_bytes, digest_value


def extract_digest_from_signed_xml(xml_bytes: bytes) -> str | None:
    try:
        root = etree.fromstring(xml_bytes)
        nodes = root.xpath(".//ds:DigestValue/text()", namespaces={"ds": NS_DS})
        return nodes[0].strip() if nodes else None
    except Exception:
        return None


def build_sunat_qr_string(
    issuer_ruc: str,
    doc_type: str,
    serie: str,
    correlativo: str,
    igv_amount: float,
    total_amount: float,
    issue_date: str,
    customer_doc_type: str,
    customer_doc_number: str,
    digest_value: str | None,
) -> str:
    """Cadena oficial QR SUNAT: RUC|TIPO|SERIE|NUM|IGV|TOTAL|FECHA|TIPODOC_CLI|NUMDOC_CLI|HASH|"""
    return (
        f"{issuer_ruc}|{doc_type}|{serie}|{correlativo}|"
        f"{float(igv_amount):.2f}|{float(total_amount):.2f}|{issue_date}|"
        f"{customer_doc_type or '0'}|{customer_doc_number or '-'}|{digest_value or ''}|"
    )


def save_artifact_file(issuer_ruc: str, issue_date: str, filename: str, content: bytes) -> str:
    """Guarda XML o CDR .zip en almacenamiento persistente organizado por RUC/Año/Mes."""
    ym = issue_date[:7] if len(issue_date) >= 7 else datetime.datetime.now().strftime("%Y-%m")
    target_dir = Path(settings.STORAGE_DIR) / issuer_ruc / ym
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return str(target_path)
