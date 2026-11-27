# -*- coding: utf-8 -*-
import io
import logging
import os
import unicodedata
from zipfile import ZipFile

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

_logger = logging.getLogger(__name__)

SUNAT_TIMEOUT = 8
SUNAT_ZIP_TIMEOUT = 120


class ResPartner(models.Model):
    _inherit = 'res.partner'

    state = fields.Selection([('ACTIVO', 'ACTIVO'),
                            ('BAJA DE OFICIO', 'BAJA DE OFICIO'),
                            ('BAJA DEFINITIVA', 'BAJA DEFINITIVA'),
                            ('BAJA PROVISIONAL', 'BAJA PROVISIONAL'),
                            ('SUSPENSION TEMPORAL', 'BAJA PROVISIONAL'),
                            ('INHABILITADO-VENT.UN', 'INHABILITADO-VENT.UN'),
                            ('BAJA MULT.INSCR. Y O', 'BAJA MULT.INSCR. Y O'),
                            ('PENDIENTE DE INI. DE', 'PENDIENTE DE INI. DE'),
                            ('OTROS OBLIGADOS', 'OTROS OBLIGADOS'),
                            ('NUM. INTERNO IDENTIF', 'NUM. INTERNO IDENTIF'),
                            ('ANUL.PROVI.-ACTO ILI', 'ANUL.PROVI.-ACTO ILI'),
                            ('ANULACION - ACTO ILI', 'ANULACION - ACTO ILI'),
                            ('BAJA PROV. POR OFICIO', 'BAJA PROV. POR OFICIO'),
                            ('ANULACION - ERROR SU', 'ANULACION - ERROR SU')], "Partner State", default="ACTIVO")
    condition = fields.Selection([('HABIDO', 'HABIDO'),
                                ('NO HABIDO', 'NO HABIDO'),
                                ('', 'NO HABIDO'),
                                ('NO HALLADO', 'NO HALLADO'),
                                ('PENDIENTE', 'PENDIENTE'),
                                ('NO HALLADO SE MUDO D', 'NO HALLADO SE MUDO D'),
                                ('NO HALLADO NO EXISTE', 'NO HALLADO NO EXISTE'),
                                ('NO HALLADO FALLECIO', 'NO HALLADO FALLECIO'),
                                ('-', 'NO HABIDO'),
                                ('NO HALLADO OTROS MOT', 'NO HALLADO OTROS MOT'),
                                ('NO APLICABLE', 'NO APLICABLE'),
                                ('NO HALLADO NRO.PUERT', 'NO HALLADO NRO.PUERT'),
                                ('NO HALLADO CERRADO', 'NO HALLADO CERRADO'),
                                ('POR VERIFICAR', 'POR VERIFICAR'),
                                ('NO HALLADO DESTINATA', 'NO HALLADO DESTINATA'),
                                ('NO HALLADO RECHAZADO', 'NO HALLADO RECHAZADO')], 'Condition')

    is_retention_agent = fields.Boolean('Es agente de retención')

    vat_consult_warning = fields.Char(
        'Aviso consulta SUNAT',
        help='Último resultado fallido de la consulta automática a SUNAT. '
             'Si está seteado, procese los datos del contacto manualmente.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        try:
            data = str(res.get('name'))
            if len(data) == 11 and data.isdigit():
                res.update({
                    'name': False,
                    'vat': data,
                })
            elif len(data) == 8 and data.isdigit():
                res.update({
                    'name': False,
                    'additional_identifiers': {'PE_DNI': data},
                })
        except Exception:
            pass
        return res

    def _sunat_session(self):
        """Sesion HTTP para SUNAT. curl_cffi impersona el fingerprint TLS de
        Chrome para pasar el challenge de Cloudflare (requests recibe 403)."""
        if curl_requests is not None:
            return curl_requests.Session(impersonate="chrome")
        _logger.warning("curl_cffi no esta instalado: SUNAT probablemente bloqueara las peticiones (403 Cloudflare)")
        return requests.Session()

    def _sunat_request(self, method, url, headers=None, timeout=SUNAT_TIMEOUT):
        """Peticion unica a SUNAT con impersonacion de Chrome y timeout."""
        if curl_requests is not None:
            return curl_requests.request(method, url, headers=headers, timeout=timeout, impersonate="chrome", verify=True)
        return requests.request(method, url, headers=headers, timeout=timeout, verify=True)

    def UnzipFileAndSearchRuc(self, vat, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
        response = self._sunat_request("GET", url, headers=headers, timeout=SUNAT_ZIP_TIMEOUT)
        # Comprobar si la descarga fue exitosa (código de estado 200)
        if response.status_code == 200:
            # Leer el archivo ZIP desde la respuesta y descomprimirlo en memoria
            with ZipFile(io.BytesIO(response.content)) as zip_ref:
                # Obtener el nombre del archivo dentro del ZIP
                text_file_name = zip_ref.filelist[0].filename
                # Obtener el contenido del archivo de texto como una sola cadena
                text_data = zip_ref.read(text_file_name).decode('iso-8859-1')
                # Dividir el contenido en líneas usando "\r" como separador
                lines = text_data.split("\r")
                # Procesar cada línea
                for line in lines:
                    line = line.strip()
                    if line:
                        # Divide la línea por el carácter "|" y obtén los campos
                        line_parts = line.split("|")
                        if len(line_parts) >= 4:
                            ruc, nombre, fecha, resolucion = line_parts[:4]
                            # Verifica si el RUC está en tu lista y realiza la acción necesaria
                            if vat == ruc:
                                if hasattr(response, 'close'):
                                    response.close()
                                return True
        else:
            _logger.error("Error al descargar el archivo ZIP para obtener datos de sunat (codigo %s, url %s).", response.status_code, url)
        if hasattr(response, 'close'):
            response.close()
        return False

    def CheckRetentionAgent(self, vat):
        url = "https://ww1.sunat.gob.pe/descarga/AgentRet/AgenRet_TXT.zip"
        self.is_retention_agent = self.UnzipFileAndSearchRuc(vat, url)

    def update_document(self):
        for rec in self:
            rec._vat_change()

    def _onchange_l10n_pe_district(self):
        """ Al elegir distrito, sincronizar ciudad y colocar el zip correcto. """
        super()._onchange_l10n_pe_district()
        self.zip = self.l10n_pe_district.code

    @api.onchange('vat', 'additional_identifiers', 'country_id')
    def _vat_change(self):
        # Odoo 20: el RUC vive en `vat` y el DNI en `additional_identifiers['PE_DNI']`
        vat = (self.vat or '').strip()
        vat = vat[2:] if vat[:2].upper() == 'PE' else vat
        dni = (self.additional_identifiers or {}).get('PE_DNI', '').strip()
        is_pe = not self.country_id or self.country_id.code == 'PE'

        if is_pe and vat and len(vat) == 11:
            # Odoo 20: `is_company` es computado; un RUC en `vat` marca el
            # contacto como compañía automáticamente.
            self.vat_consult_warning = False
            self.ValidarRUC(vat)
            try:
                self.ConsultarRUC(vat)
                self.CheckRetentionAgent(vat)
            except UserError as e:
                self.vat_consult_warning = self.env._(
                    "No se pudo obtener la información de SUNAT para el RUC %(ruc)s. Ingrese los datos manualmente.\n%(error)s",
                    ruc=vat, error=e,
                )
        elif is_pe and dni:
            self.vat_consult_warning = False
            if len(dni) != 8:
                raise UserError(self.env._('El DNI introducido es incorrecto.'))
            self.ConsultarDNI(dni)

    @api.onchange('parent_id')
    def _onchange_parent_id_address(self):
        if self.parent_id:
            self.city_id = self.parent_id.city_id.id
            self.l10n_pe_district = self.parent_id.l10n_pe_district.id

    def _sofia_gateway_headers(self):
        headers = {'Accept': 'application/json'}
        key = (os.environ.get('INTERNAL_SERVICE_KEY') or '').strip()
        if key:
            headers['X-Internal-Service-Key'] = key
        return headers

    def ConsultarDNI(self, numeroDNI):
        # 1. Intentar primero mediante Sofia Gateway Hub centralizado (Decolecta + caché compartido)
        gw_url = (os.environ.get('SOFIA_GATEWAY_URL') or '').strip().rstrip('/')
        if gw_url:
            try:
                gw_res = requests.get(
                    f'{gw_url}/api/v1/lookup/dni/{numeroDNI}',
                    headers=self._sofia_gateway_headers(),
                    timeout=SUNAT_TIMEOUT,
                )
                if gw_res.status_code == 200:
                    gw_data = gw_res.json()
                    if gw_data.get('full_name'):
                        self.name = gw_data['full_name']
                        return
            except Exception as exc:
                _logger.info("Sofia Gateway DNI %s fallback a proveedor directo: %s", numeroDNI, exc)

        # 2. Fallback directo a apis.net.pe
        try:
            # realizamos la consulta a la api
            result = requests.get(f'https://api.apis.net.pe/v1/dni?numero={numeroDNI}', timeout=SUNAT_TIMEOUT)
            # convertimos el resultado a un diccionario
            if result.status_code == 404:
                pass  # raise UserError(self.env._('El servidor no obtiene respuesta para el DNI consultado.'))
            jsonedResponse = result.json()
            full_name = jsonedResponse.get('nombre')
            if not full_name:
                parts = [jsonedResponse.get('nombres', ''), jsonedResponse.get('apellidoPaterno', ''), jsonedResponse.get('apellidoMaterno', '')]
                full_name = ' '.join(p for p in parts if p).strip()
            self.name = full_name
        except UserError:
            raise
        except Exception as e:
            _logger.warning("No se pudo consultar el DNI %s en api.apis.net.pe: %s", numeroDNI, e)
            self.vat_consult_warning = self.env._(
                "No se pudo obtener la información del DNI %(dni)s. Ingrese los datos manualmente.", dni=numeroDNI,
            )

    def ValidarRUC(self, numeroRUC):
        tipoRespuesta = 2
        mensajeRespuesta = ""
        nValor = len(numeroRUC)
        if nValor == 11:
            if numeroRUC.isdigit():
                tipoRespuesta = 1
            else:
                mensajeRespuesta = self.env._("El número de RUC '%(ruc)s' solo debe tener caracteres numéricos.", ruc=numeroRUC)
        else:
            mensajeRespuesta = self.env._(
                "El número de RUC '%(ruc)s' tiene %(length)d caracteres y debe tener 11.",
                ruc=numeroRUC, length=nValor,
            )
        if tipoRespuesta > 1:
            raise UserError(mensajeRespuesta)
        return tipoRespuesta, mensajeRespuesta

    def ObtenerDatosRUC(self, contenidoHTML):
        oEnSUNAT = EnSUNAT()
        nombreInicio = ""
        nombreFin = ""
        posicion = 0
        arrResultado = list()

        nombreInicio = "<HEAD><TITLE>"
        nombreFin = "</TITLE></HEAD>"
        contenidoBusqueda = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        if contenidoBusqueda == ".:: Pagina de Mensajes ::.":
            nombreInicio = "<p class=\"error\">"
            nombreFin = "</p>"
            oEnSUNAT.TipoRespuesta = 2
            oEnSUNAT.MensajeRespuesta = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        elif contenidoBusqueda == ".:: Pagina de Error ::.":
            nombreInicio = "<p class=\"error\">"
            nombreFin = "</p>"
            oEnSUNAT.TipoRespuesta = 3
            oEnSUNAT.MensajeRespuesta = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        else:
            oEnSUNAT.TipoRespuesta = 2

            nombreInicio = "<div class=\"list-group\">"
            nombreFin = "<div class=\"panel-footer text-center\">"
            contenidoBusqueda = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
            if contenidoBusqueda == "":
                nombreInicio = "<strong>"
                nombreFin = "</strong>"
                oEnSUNAT.MensajeRespuesta = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
                if oEnSUNAT.MensajeRespuesta == "":
                    oEnSUNAT.MensajeRespuesta = "No se puede obtener los datos del RUC, porque no existe la clase principal \"list-group\" en el contenido HTML"
            else:
                nombreInicio = "<h4 class=\"list-group-item-heading\">"
                nombreFin = "</h4>"
                posicion = 0

                arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                if len(arrResultado) > 0:
                    posicion = int(arrResultado[0])
                    arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                    posicion = int(arrResultado[0])
                    oEnSUNAT.RUC = arrResultado[1]
                    oEnSUNAT.TipoRespuesta = 1
                else:
                    oEnSUNAT.MensajeRespuesta = "No se puede obtener la \"Razon Social\", porque no existe la clase \"list-group-item-heading\" en el contenido HTML"

                if oEnSUNAT.TipoRespuesta == 1:
                    '''
                    # Mensaje cuando el estado es "BAJA DE OFICIO" caso contrario inicia con "Tipo Contribuyente"
                    # Tipo Contribuyente
                    # Nombre Comercial
                    # Fecha de Inscripción
                    # Fecha de Inicio de Actividades
                    # Estado del Contribuyente
                    # Condición del Contribuyente
                    # Domicilio Fiscal
                    # Sistema Emisión de Comprobante
                    # Actividad Comercio Exterior
                    # Sistema Contabilidiad
                    # Emisor electrónico desde:
                    # Comprobantes Electrónicos:
                    # Afiliado al PLE desde
                    # n/a
                    '''
                    lCadena = list()
                    nombreInicio = "<p class=\"list-group-item-text\">"
                    nombreFin = "</p>"
                    posicion = 0
                    arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                    while len(arrResultado) > 0:
                        posicion = int(arrResultado[0])
                        lCadena.append(arrResultado[1].strip())
                        arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                    if len(lCadena) == 0:
                        oEnSUNAT.TipoRespuesta = 2
                        oEnSUNAT.MensajeRespuesta = "No se puede obtener los datos básicos, porque no existe la clase \"list-group-item-text\" en el contenido HTML"
                    else:
                        inicio = 0
                        if len(lCadena) > 14:  # Si estado es "BAJA DE OFICIO" caso contrario es 14
                            inicio = 1
                        oEnSUNAT.TipoContribuyente = lCadena[inicio]
                        oEnSUNAT.NombreComercial = lCadena[inicio + 1]
                        oEnSUNAT.FechaInscripcion = lCadena[inicio + 2]
                        oEnSUNAT.FechaInicioActividades = lCadena[inicio + 3]
                        oEnSUNAT.EstadoContribuyente = lCadena[inicio + 4]
                        oEnSUNAT.CondicionContribuyente = lCadena[inicio + 5]
                        oEnSUNAT.DomicilioFiscal = lCadena[inicio + 6]
                        oEnSUNAT.SistemaEmisionComprobante = lCadena[inicio + 7]
                        oEnSUNAT.ActividadComercioExterior = lCadena[inicio + 8]
                        oEnSUNAT.SistemaContabilidiad = lCadena[inicio + 9]
                        oEnSUNAT.EmisorElectronicoDesde = lCadena[inicio + 10]
                        oEnSUNAT.ComprobantesElectronicos = lCadena[inicio + 11]
                        oEnSUNAT.AfiliadoPLEDesde = lCadena[inicio + 12]

                        '''
                        # Actividad(es) Económica(s)
                        # Comprobantes de Pago c/aut. de impresión (F. 806 u 816)
                        # Sistema de Emisión Electrónica # (opcional, em algunos casos no aparece)
                        # Padrones
                        '''
                        lCadena = list()
                        nombreInicio = "<tbody>"
                        nombreFin = "</tbody>"
                        posicion = 0
                        arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                        while len(arrResultado) > 0:
                            posicion = int(arrResultado[0])
                            lCadena.append(arrResultado[1].strip().replace('\r\n', ' ').replace('\t', ' '))
                            arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                        if len(lCadena) == 0:
                            oEnSUNAT.TipoRespuesta = 2
                            oEnSUNAT.MensajeRespuesta = "No se puede obtener los datos de las tablas, porque no existe el tag \"tbody\" en el contenido HTML"
                        else:
                            oEnSUNAT.ActividadesEconomicas = lCadena[0]
                            oEnSUNAT.ComprobantesPago = lCadena[1]
                            if len(lCadena) == 4:
                                oEnSUNAT.SistemaEmisionElectronica = lCadena[2]
                                oEnSUNAT.Padrones = lCadena[3]
                            else:
                                oEnSUNAT.Padrones = lCadena[2]

        return oEnSUNAT

    def ObtenerDatosRepresentantesLegales(self, contenidoHTML):
        oEnSUNAT = EnSUNAT()
        nombreInicio = ""
        nombreFin = ""
        posicion = 0
        arrResultado = list()

        nombreInicio = "<HEAD><TITLE>"
        nombreFin = "</TITLE></HEAD>"
        contenidoBusqueda = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        if contenidoBusqueda == ".:: Pagina de Mensajes ::.":
            nombreInicio = "<p class=\"error\">"
            nombreFin = "</p>"
            oEnSUNAT.TipoRespuesta = 2
            oEnSUNAT.MensajeRespuesta = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        elif contenidoBusqueda == ".:: Pagina de Error ::.":
            nombreInicio = "<p class=\"error\">"
            nombreFin = "</p>"
            oEnSUNAT.TipoRespuesta = 3
            oEnSUNAT.MensajeRespuesta = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, nombreInicio, nombreFin)
        else:
            oEnSUNAT.TipoRespuesta = 2
            nombreInicio = "<td align=\""
            nombreFin = "</td>"
            posicion = 0
            rep = {}
            contador = 0
            while True:
                arrResultado = self.ExtraerContenidoEntreTag(contenidoHTML, posicion, nombreInicio, nombreFin, False)
                contenidoBusqueda = self.ExtraerContenidoEntreTagString(contenidoHTML, posicion, nombreInicio, nombreFin)
                if len(arrResultado) > 0:
                    posicion = int(arrResultado[0])
                    rep[contador] = contenidoBusqueda[contenidoBusqueda.find('>')+1:].strip()
                    contador += 1
                    if contador % 5 == 0:
                        oEnSUNAT.RepresentantesLegales.append(rep)
                        contador = 0
                        rep = {}
                if contenidoBusqueda == "":
                    break
                else:
                    oEnSUNAT.TipoRespuesta = 1
        return oEnSUNAT

    def normalizar_texto(self, texto):
        # Normalizar el texto para quitar tildes
        return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')

    def ConsultarContenidoRUC(self, sesion, urlReferencia, numeroRUC, numeroRandom):
        tipoRespuesta = 2
        mensajeRespuesta = ""

        payload = {}
        headers = {
            'Host': 'e-consultaruc.sunat.gob.pe',
            'Origin': 'https://e-consultaruc.sunat.gob.pe',
            'Referer': urlReferencia,
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
            'sec-ch-ua-mobile': '?0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        }
        url = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias?accion=consPorRuc&nroRuc=%s&contexto=ti-it&modo=1&numRnd=%s" % (numeroRUC, numeroRandom)
        response = sesion.request("POST", url, headers=headers, data=payload, verify=True, timeout=SUNAT_TIMEOUT)
        contenidoHTML = response.text

        if response.status_code == 200:
            oEnSUNAT = self.ObtenerDatosRUC(contenidoHTML)
            if oEnSUNAT.TipoRespuesta == 1:
                splited = oEnSUNAT.RUC.split('-')
                name = splited[1]
                # Si el nombre lleva un guión agregamos el resto
                if len(splited) > 1:
                    for i in range(2, len(splited)):
                        name += '-' + splited[i]
                self.name = name.strip()
                country_id = self.env['res.country'].search([('code', '=', 'PE')])
                # SUNAT rellena los campos con espacios; a veces omite el separador
                # entre calle y departamento. Normalizamos y parseamos desde el final.
                segs = [" ".join(s.split()) for s in oEnSUNAT.DomicilioFiscal.split('-')]
                if oEnSUNAT.DomicilioFiscal != '-' and len(segs) >= 3:
                    district = segs[-1].title()
                    if '(' in district:
                        district = district.split('(')[0].strip()
                    city = segs[-2].title()
                    if '(' in city:
                        city = city.split('(')[0].strip()
                    if len(segs) >= 4:
                        state = segs[-3].title()
                    else:
                        # Con 3 segmentos el departamento queda pegado al final de la calle
                        state = segs[0].rsplit(' ', 1)[-1].title()
                    if '(' in state:
                        state = state.split('(')[0].strip()
                    # Solo para el callao
                    if city == 'Prov. Const. Del Callao':
                        district = 'Callao'
                        city = 'Callao'
                        state = 'Callao'
                else:
                    district = ''
                    city = ''
                    state = ''
                if '(' in oEnSUNAT.DomicilioFiscal:
                    street = segs[0].split('(')[0].strip() if segs else ''
                else:
                    street = segs[0] if segs else ''
                    if len(segs) == 3 and street:
                        # quitar el departamento pegado al final de la calle
                        street = street.rsplit(' ', 1)[0]

                # Mapeo de direccion solo si SUNAT reporto alguna (RUCs sin domicilio traen '-')
                hay_direccion = bool(district or city or state)
                state_id = False
                city_id = False
                district_id = False
                final_district = False
                if hay_direccion:
                    state_id = self.env['res.country.state'].search([('name', '=ilike', state), ('country_id', '=', country_id.id)], limit=1) if state else False
                    city_id = self.env['res.city'].search([('name', '=ilike', city), ('country_id', '=', country_id.id)], limit=1) if city else False
                    district_id = self.env['l10n_pe.res.city.district'].search([('name', '=ilike', district), ('city_id', '=', city_id.id if city_id else False)], limit=1) if district else False

                    if district_id and len(district_id) > 1:
                        final_district = district_id[0]
                        for dis in district_id:
                            if dis.name.upper() == district.upper():
                                final_district = dis
                    else:
                        final_district = district_id

                    if state and not state_id:
                        states_all = self.env['res.country.state'].search([('country_id', '=', country_id.id)])
                        for st in states_all:
                            st_name = self.normalizar_texto(st.name).strip()
                            r_name = self.normalizar_texto(state).strip()
                            if st_name.lower() in r_name.lower():
                                state_id = st.id
                                break
                    if city and not city_id:
                        city_id_all = self.env['res.city'].search([('country_id', '=', country_id.id), ('state_id', '=', state_id)])
                        for st in city_id_all:
                            st_name = self.normalizar_texto(st.name).strip()
                            r_name = self.normalizar_texto(city).strip()
                            if st_name.lower() in r_name.lower():
                                city_id = st.id
                                break
                    if district and not district_id and city_id:
                        district_all = self.env['l10n_pe.res.city.district'].search([('city_id', '=', city_id.id)])
                        for st in district_all:
                            st_name = self.normalizar_texto(st.name).strip()
                            r_name = self.normalizar_texto(district).strip()
                            if st_name.lower() in r_name.lower():
                                district_id = st.id
                                break
                        if not district_id:
                            final_district = False

                self.country_id = country_id
                if hay_direccion:
                    self.l10n_pe_district = final_district if final_district else False
                    self.city_id = city_id if city_id else False
                    self.state_id = state_id if state_id else False
                    self.street = street or ''
                    self.zip = final_district.code if final_district else ''
                self.state = oEnSUNAT.EstadoContribuyente
                self.condition = oEnSUNAT.CondicionContribuyente

                tipoRespuesta = 1
            else:
                tipoRespuesta = oEnSUNAT.TipoRespuesta
                mensajeRespuesta = self.env._(
                    "No se pudieron obtener los datos para RUC %(ruc)s.\nDetalles: %(details)s",
                    ruc=numeroRUC, details=oEnSUNAT.MensajeRespuesta,
                )
                raise UserError(mensajeRespuesta)

        return tipoRespuesta, mensajeRespuesta, response.status_code

    def ConsultarLocalesAnexos(self, sesion, urlReferencia, desRuc, numeroRUC, numeroRandom):
        tipoRespuesta = 2
        mensajeRespuesta = ""

        payload = {}
        headers = {
            'Host': 'e-consultaruc.sunat.gob.pe',
            'Origin': 'https://e-consultaruc.sunat.gob.pe',
            'Referer': urlReferencia,
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
            'sec-ch-ua-mobile': '?0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        }
        url = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias?accion=getLocAnex&desRuc=%s&nroRuc=%s&contexto=ti-it&modo=1&numRnd=%s" % (desRuc, numeroRUC, numeroRandom)
        response = sesion.request("POST", url, headers=headers, data=payload, verify=True, timeout=SUNAT_TIMEOUT)
        contenidoHTML = response.text

        if response.status_code == 200:
            oEnSUNAT = self.ObtenerDatosLocalesAnexos(contenidoHTML)
            if oEnSUNAT.TipoRespuesta == 1:

                if oEnSUNAT.LocalesAnexos and self.is_company:
                    for local in oEnSUNAT.LocalesAnexos:
                        contact = {}
                        contact['name'] = local[0] + ' - ' + local[1]
                        district = local[2].split('-')[-1].strip().title()
                        city = local[2].split('-')[-2].strip().title()
                        state = local[2].split('-')[-3].strip().title()
                        # Solo para el callao
                        if city == 'Prov. Const. Del Callao':
                            district = 'Callao'
                            city = 'Callao'
                            state = 'Callao'
                        country_id = self.env['res.country'].search([('code', '=', 'PE')])
                        state_id = False
                        city_id = False
                        district_id = False
                        for i in range(1, len(state)):
                            state_id = self.env['res.country.state'].search([('name', 'like', state), ('country_id', '=', country_id.id)], limit=1) if state else False
                            if state_id:
                                break
                            else:
                                state = state[1:]
                        if city and state_id:
                            city_id = self.env['res.city'].search([('name', '=ilike', city), ('state_id', '=', state_id.id), ('country_id', '=', country_id.id)], limit=1)
                        if district and city_id:
                            district_id = self.env['l10n_pe.res.city.district'].search([('name', '=ilike', district), ('city_id', '=', city_id.id)], limit=1)
                        if self.search_count([('name', '=', contact['name']), ('parent_id', '=', self.id)]) == 0:
                            contact['street'] = local[2].replace('  ', ' ').replace('  ', '').strip()
                            contact['l10n_pe_district'] = district_id.id if district_id else False
                            contact['city_id'] = city_id.id if city_id else False
                            contact['state_id'] = state_id.id if state_id else False
                            contact['country_id'] = country_id.id
                            contact['zip'] = district_id.code if district_id else ''
                            contact['type'] = 'delivery'
                            contact['parent_id'] = self.id
                            self.child_ids = [(0, 0, contact)]
                tipoRespuesta = 1
            else:
                tipoRespuesta = oEnSUNAT.TipoRespuesta
                mensajeRespuesta = self.env._(
                    "No se pudieron obtener los datos para RUC %(ruc)s.\nDetalles: %(details)s",
                    ruc=numeroRUC, details=oEnSUNAT.MensajeRespuesta,
                )
                raise UserError(mensajeRespuesta)

        return tipoRespuesta, mensajeRespuesta, response.status_code

    def ConsultarRUC_ApiNetPe(self, numeroRUC):
        """Consulta RUC mediante Sofia Gateway Hub (prioridad #1, caché compartido + Decolecta)
        con fallback a apis.net.pe. Retorna True si obtuvo datos o False para fallback a SUNAT."""
        gw_url = (os.environ.get('SOFIA_GATEWAY_URL') or '').strip().rstrip('/')
        if gw_url:
            try:
                gw_res = requests.get(
                    f'{gw_url}/api/v1/lookup/ruc/{numeroRUC}',
                    headers=self._sofia_gateway_headers(),
                    timeout=6,
                )
                if gw_res.status_code == 200:
                    data = gw_res.json()
                    if data.get('business_name'):
                        self.name = data.get('business_name', '')
                        self.street = data.get('address', '')
                        self.state = data.get('status', '')
                        self.condition = data.get('condition', '')
                        country_pe = self.env['res.country'].search([('code', '=', 'PE')], limit=1)
                        if country_pe:
                            self.country_id = country_pe.id
                        ubigeo = data.get('ubigeo', '')
                        if ubigeo:
                            district = self.env['l10n_pe.res.city.district'].search([('code', '=', ubigeo)], limit=1)
                            if district:
                                self.l10n_pe_district = district.id
                                self.zip = district.code
                                if district.city_id:
                                    self.city_id = district.city_id.id
                                    if district.city_id.state_id:
                                        self.state_id = district.city_id.state_id.id
                        return True
            except Exception as e:
                _logger.info("Sofia Gateway RUC %s fallback a apis.net.pe: %s", numeroRUC, e)

        try:
            result = requests.get(f'https://api.apis.net.pe/v1/ruc?numero={numeroRUC}', timeout=6)
            if result.status_code == 200:
                data = result.json()
                self.name = data.get('nombre', '')
                self.street = data.get('direccion', '')
                self.state = data.get('estado', '')
                self.condition = data.get('condicion', '')

                country_pe = self.env['res.country'].search([('code', '=', 'PE')], limit=1)
                if country_pe:
                    self.country_id = country_pe.id

                ubigeo = data.get('ubigeo', '')
                if ubigeo:
                    district = self.env['l10n_pe.res.city.district'].search([('code', '=', ubigeo)], limit=1)
                    if district:
                        self.l10n_pe_district = district.id
                        self.zip = district.code
                        if district.city_id:
                            self.city_id = district.city_id.id
                            if district.city_id.state_id:
                                self.state_id = district.city_id.state_id.id
                return True
        except Exception as e:
            _logger.info("Consulta API apis.net.pe fallo para RUC %s: %s", numeroRUC, e)
        return False

    def ConsultarRUC(self, numeroRUC):
        # 1. Intentar primero con la API REST (alta velocidad y sin bloqueos de Cloudflare)
        if self.ConsultarRUC_ApiNetPe(numeroRUC):
            return

        # 2. Si la API no responde o no encuentra el RUC, intentar scraping directo de SUNAT
        return self._ConsultarRUC_SUNAT(numeroRUC)

    def _ConsultarRUC_SUNAT(self, numeroRUC):
        mensajeRespuesta = ""

        try:
            urlInicial = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
            payload = {}
            headers = {
                'Host': 'e-consultaruc.sunat.gob.pe',
                'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
                'sec-ch-ua-mobile': '?0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
            }

            sesion = self._sunat_session()
            response = sesion.request("GET", urlInicial, headers=headers, data=payload, verify=True, timeout=SUNAT_TIMEOUT)

            if response.status_code == 200:
                payload = {}
                headers = {
                    'Host': 'e-consultaruc.sunat.gob.pe',
                    'Origin': 'https://e-consultaruc.sunat.gob.pe',
                    'Referer': urlInicial,
                    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
                    'sec-ch-ua-mobile': '?0',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                }

                numeroDNI = "12345678"  # cualquier número DNI pero que exista en SUNAT.
                url = f"https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias?accion=consPorTipdoc&razSoc=&nroRuc=&nrodoc={numeroDNI}&contexto=ti-it&modo=1&search1=&rbtnTipo=2&tipdoc=1&search2={numeroDNI}&search3=&codigo="

                contenidoHTML = ""
                nIntentos = 0
                codigoEstado = 401
                consRuc = False
                # Validamos que intente hasta 5 veces si el código de respuesta es 401 Unauthorized
                while nIntentos < 5 and codigoEstado == 401:
                    response = sesion.request("POST", url, headers=headers, data=payload, verify=True, timeout=SUNAT_TIMEOUT)
                    codigoEstado = response.status_code
                    contenidoHTML = response.text
                    nIntentos += 1

                if not consRuc:
                    numeroRandom = self.ExtraerContenidoEntreTagString(contenidoHTML, 0, "name=\"numRnd\" value=\"", "\">")
                    # Validamos que intente hasta 5 veces si el código de respuesta es 401 Unauthorized
                    nIntentos = 0
                    codigoEstado = 401
                    while nIntentos < 5 and not consRuc:
                        tipoRespuesta, mensajeRespuesta, codigoEstado = self.ConsultarContenidoRUC(sesion, urlInicial, numeroRUC, numeroRandom)
                        nIntentos += 1
                        if codigoEstado == 200:
                            consRuc = True
                else:
                    mensajeRespuesta = "Ocurrió un inconveniente (%s) al consultar el número random del RUC %s.\nDetalle: %s" % (response.status_code, numeroRUC, contenidoHTML)
                    raise UserError(mensajeRespuesta)
            else:
                _logger.error("SUNAT devolvio codigo %s para GET %s (posible bloqueo Cloudflare).", response.status_code, urlInicial)
                raise UserError(self.env._(
                    "No se pudo conectar con SUNAT (código %(code)s). Intente nuevamente en unos minutos.",
                    code=response.status_code,
                ))
        except UserError:
            raise
        except Exception as e:
            _logger.exception("Error consultando RUC %s en SUNAT", numeroRUC)
            raise UserError(self.env._(
                "Ocurrió un error consultando el RUC %(ruc)s en SUNAT:\n%(error)s",
                ruc=numeroRUC, error=e,
            ))

    def ExtraerContenidoEntreTagString(self, cadena, posicion, nombreInicio, nombreFin, sensitivo=False):
        respuesta = ""
        if sensitivo:
            cadena2 = cadena.lower()
            nombreInicio = nombreInicio.lower()
            nombreFin = nombreFin.lower()
            posicionInicio = cadena2.find(nombreInicio, posicion)
            if posicionInicio > -1:
                posicionInicio += len(nombreInicio)
                posicionFin = cadena2.find(nombreFin, posicionInicio)
                if posicionFin > -1:
                    respuesta = cadena[posicionInicio:posicionFin]
        else:
            posicionInicio = cadena.find(nombreInicio, posicion)
            if posicionInicio > -1:
                posicionInicio += len(nombreInicio)
                posicionFin = cadena.find(nombreFin, posicionInicio)
                if posicionFin > -1:
                    respuesta = cadena[posicionInicio:posicionFin]
        return respuesta

    def ExtraerContenidoEntreTag(self, cadena, posicion, nombreInicio, nombreFin, sensitivo=False):
        respuesta = list()
        if sensitivo:
            cadena2 = cadena.lower()
            nombreInicio = nombreInicio.lower()
            nombreFin = nombreFin.lower()
            posicionInicio = cadena2.find(nombreInicio, posicion)
            if posicionInicio > -1:
                posicionInicio += len(nombreInicio)
                posicionFin = cadena2.find(nombreFin, posicionInicio)
                if posicionFin > -1:
                    posicion = posicionFin + len(nombreFin)
                    respuesta = [posicion, cadena[posicionInicio:posicionFin]]
        else:
            posicionInicio = cadena.find(nombreInicio, posicion)
            if posicionInicio > -1:
                posicionInicio += len(nombreInicio)
                posicionFin = cadena.find(nombreFin, posicionInicio)
                if posicionFin > -1:
                    posicion = posicionFin + len(nombreFin)
                    respuesta = [posicion, cadena[posicionInicio:posicionFin]]
        return respuesta


class EnSUNAT(object):
    def __init__(self):
        self.TipoRespuesta = 0
        self.MensajeRespuesta = ""
        self.RUC = ""
        self.TipoContribuyente = ""
        self.NombreComercial = ""
        self.FechaInscripcion = ""
        self.FechaInicioActividades = ""
        self.EstadoContribuyente = ""
        self.CondicionContribuyente = ""
        self.DomicilioFiscal = ""
        self.SistemaEmisionComprobante = ""
        self.ActividadComercioExterior = ""
        self.SistemaContabilidiad = ""
        self.ActividadesEconomicas = ""
        self.ComprobantesPago = ""
        self.SistemaEmisionElectronica = ""
        self.EmisorElectronicoDesde = ""
        self.ComprobantesElectronicos = ""
        self.AfiliadoPLEDesde = ""
        self.Padrones = ""
        self.RepresentantesLegales = []
        self.LocalesAnexos = []
