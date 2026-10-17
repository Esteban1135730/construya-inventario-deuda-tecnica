# -*- coding: utf-8 -*-
"""
Sistema de gestión de inventario — versión refactorizada.
Mantiene el comportamiento observable de la API pública.
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constantes de tipos de operación
# ---------------------------------------------------------------------------

TIPO_ENTRADA = "ENTRADA"
TIPO_SALIDA = "SALIDA"
TIPO_AJUSTE = "AJUSTE"
TIPO_TRANSFERENCIA = "TRANSFERENCIA"

TIPOS_SOPORTADOS = frozenset({TIPO_ENTRADA, TIPO_SALIDA, TIPO_AJUSTE, TIPO_TRANSFERENCIA})

CATEGORIA_POR_DEFECTO = "GENERAL"
MAX_MOVIMIENTOS_INFORME = 10

# ---------------------------------------------------------------------------
# Constantes de mensajes
# ---------------------------------------------------------------------------

MSG_TIPO_OBLIGATORIO = "El tipo de operación es obligatorio."
MSG_TIPO_NO_SOPORTADO = "Tipo de operación no soportado: {tipo}."
MSG_CODIGO_OBLIGATORIO = "El código del producto es obligatorio."
MSG_BODEGA_OBLIGATORIA = "La bodega es obligatoria."
MSG_CANTIDAD_NUMERICA = "La cantidad debe ser numérica."
MSG_CANTIDAD_MAYOR_CERO = "La cantidad debe ser mayor que cero."
MSG_COSTO_NUMERICO = "El costo debe ser numérico."
MSG_COSTO_NEGATIVO = "El costo no puede ser negativo."
MSG_NOMBRE_OBLIGATORIO = "El nombre es obligatorio para registrar un producto nuevo."
MSG_STOCK_MINIMO_NUMERICO = "El stock mínimo debe ser numérico."
MSG_STOCK_MINIMO_NEGATIVO = "El stock mínimo no puede ser negativo."
MSG_PRODUCTO_NO_EXISTE = "El producto {codigo} no existe en el inventario."
MSG_STOCK_INSUFICIENTE = (
    "Stock insuficiente para {codigo} en {bodega}: "
    "disponible {disponible}, solicitado {solicitado}."
)
MSG_FORZAR_BOOL = "El indicador forzar debe ser verdadero o falso."
MSG_AJUSTE_NEGATIVO = "La cantidad ajustada no puede ser negativa."
MSG_BODEGA_DESTINO_OBLIGATORIA = "La bodega de destino es obligatoria."
MSG_BODEGAS_DISTINTAS = "La bodega de origen y destino deben ser distintas."

MSG_ENTRADA_OK = "Entrada registrada para {codigo} en {bodega}. Stock resultante: {stock}."
MSG_SALIDA_OK = "Salida registrada para {codigo} en {bodega}. Stock resultante: {stock}."
MSG_AJUSTE_OK = "Ajuste registrado para {codigo} en {bodega}. Stock resultante: {stock}."
MSG_TRANSFERENCIA_OK = (
    "Transferencia registrada para {codigo} desde {bodega} hacia {destino}. "
    "Stock origen: {stock_origen}. Stock destino: {stock_destino}."
)


@dataclass
class Producto:
    nombre: str
    categoria: str
    costo_promedio: float
    stock_minimo: float
    stock_por_bodega: Dict[str, float] = field(default_factory=dict)

    def stock_total(self) -> float:
        return sum(float(v) for v in self.stock_por_bodega.values())

    def stock_en_bodega(self, bodega: str) -> float:
        return float(self.stock_por_bodega.get(bodega, 0))

    def bajo_minimo(self) -> bool:
        return self.stock_total() < float(self.stock_minimo)


@dataclass
class Movimiento:
    id: int
    tipo: str
    codigo: str
    bodega: str
    bodega_destino: str
    cantidad: float
    costo: float
    costo_promedio_resultante: float
    stock_resultante: float
    responsable: str
    motivo: str
    cliente: str
    fecha: datetime.datetime
    stock_destino_resultante: Optional[float] = None

    def a_dict(self) -> Dict[str, Any]:
        datos: Dict[str, Any] = {
            "id": self.id,
            "tipo": self.tipo,
            "codigo": self.codigo,
            "bodega": self.bodega,
            "bodega_destino": self.bodega_destino,
            "cantidad": self.cantidad,
            "costo": self.costo,
            "costo_promedio_resultante": self.costo_promedio_resultante,
            "stock_resultante": self.stock_resultante,
            "responsable": self.responsable,
            "motivo": self.motivo,
            "cliente": self.cliente,
            "fecha": self.fecha,
        }
        if self.stock_destino_resultante is not None:
            datos["stock_destino_resultante"] = self.stock_destino_resultante
        return datos


@dataclass
class SolicitudOperacion:
    tipo: str
    codigo: str
    nombre: str
    categoria: str
    costo: Any
    cantidad: Any
    stock_minimo: Any
    bodega: str
    bodega_destino: str
    responsable: str
    motivo: str
    cliente: str
    fecha: Optional[datetime.datetime]
    forzar: bool

    @classmethod
    def desde_parametros(
        cls,
        tipo,
        codigo,
        nombre="",
        categoria="",
        costo=0,
        cantidad=0,
        stock_minimo=0,
        bodega="",
        bodega_destino="",
        responsable="",
        motivo="",
        cliente="",
        fecha=None,
        forzar=False,
    ) -> SolicitudOperacion:
        return cls(
            tipo=tipo,
            codigo=codigo,
            nombre=nombre,
            categoria=categoria,
            costo=costo,
            cantidad=cantidad,
            stock_minimo=stock_minimo,
            bodega=bodega,
            bodega_destino=bodega_destino,
            responsable=responsable,
            motivo=motivo,
            cliente=cliente,
            fecha=fecha,
            forzar=forzar,
        )


class SistemaGestionInventario:
    """Gestión de inventario con operaciones ENTRADA, SALIDA, AJUSTE y TRANSFERENCIA."""

    def __init__(self, reloj: Optional[Callable[[], datetime.datetime]] = None):
        self._reloj = reloj if reloj is not None else datetime.datetime.now
        self._productos: Dict[str, Producto] = {}
        self._movimientos: List[Movimiento] = []
        self._contador_movimientos = 0

    def procesar_operacion_completa(
        self,
        tipo,
        codigo,
        nombre="",
        categoria="",
        costo=0,
        cantidad=0,
        stock_minimo=0,
        bodega="",
        bodega_destino="",
        responsable="",
        motivo="",
        cliente="",
        fecha=None,
        forzar=False,
    ):
        solicitud = SolicitudOperacion.desde_parametros(
            tipo,
            codigo,
            nombre,
            categoria,
            costo,
            cantidad,
            stock_minimo,
            bodega,
            bodega_destino,
            responsable,
            motivo,
            cliente,
            fecha,
            forzar,
        )
        error = self._validar_comunes(solicitud)
        if error is not None:
            return error

        tipo_norm = str(solicitud.tipo).strip().upper()
        codigo_norm = str(solicitud.codigo).strip().upper().replace(" ", "")
        bodega_norm = str(solicitud.bodega).strip()
        cantidad_num = float(solicitud.cantidad)

        if tipo_norm == TIPO_ENTRADA:
            return self._procesar_entrada(
                solicitud, codigo_norm, bodega_norm, cantidad_num
            )
        if tipo_norm == TIPO_SALIDA:
            return self._procesar_salida(
                solicitud, codigo_norm, bodega_norm, cantidad_num
            )
        if tipo_norm == TIPO_AJUSTE:
            return self._procesar_ajuste(
                solicitud, codigo_norm, bodega_norm, cantidad_num
            )
        if tipo_norm == TIPO_TRANSFERENCIA:
            return self._procesar_transferencia(
                solicitud, codigo_norm, bodega_norm, cantidad_num
            )

        return self._respuesta_error(
            tipo_norm,
            codigo_norm,
            bodega_norm,
            solicitud.bodega_destino,
            MSG_TIPO_NO_SOPORTADO.format(tipo=tipo_norm),
        )

    def consultar_stock(self, codigo=None, bodega=None):
        if codigo is None:
            resultado = {}
            for cod, prod in self._productos.items():
                resultado[cod] = self._producto_a_dict(prod)
            return resultado

        cod = str(codigo).strip().upper().replace(" ", "")
        if cod not in self._productos:
            return None

        prod = self._productos[cod]
        if bodega is not None:
            b = str(bodega).strip()
            return prod.stock_en_bodega(b)
        return self._producto_a_dict(prod)

    def valorizar(self, bodega=None):
        total = 0.0
        detalle = []
        for cod, prod in self._productos.items():
            if bodega is None:
                stock = prod.stock_total()
            else:
                b = str(bodega).strip()
                stock = prod.stock_en_bodega(b)
            valor = stock * float(prod.costo_promedio)
            total += valor
            detalle.append(
                {
                    "codigo": cod,
                    "nombre": prod.nombre,
                    "stock": stock,
                    "costo_promedio": prod.costo_promedio,
                    "valor": round(valor, 2),
                }
            )
        return {"total": round(total, 2), "detalle": detalle}

    def productos_bajo_minimo(self):
        bajo = []
        for cod, prod in self._productos.items():
            stock_total = prod.stock_total()
            if stock_total < float(prod.stock_minimo):
                bajo.append(
                    {
                        "codigo": cod,
                        "nombre": prod.nombre,
                        "stock_total": stock_total,
                        "stock_minimo": prod.stock_minimo,
                        "faltante": float(prod.stock_minimo) - stock_total,
                    }
                )
        return bajo

    def obtener_movimientos(self, codigo=None, bodega=None):
        movs = []
        for movimiento in self._movimientos:
            if codigo is not None:
                cod = str(codigo).strip().upper().replace(" ", "")
                if movimiento.codigo != cod:
                    continue
            if bodega is not None:
                b = str(bodega).strip()
                if movimiento.bodega != b and movimiento.bodega_destino != b:
                    continue
            movs.append(copy.deepcopy(movimiento.a_dict()))
        return movs

    def generar_informe_operativo(self, bodega=None):
        if bodega is None:
            movs = [copy.deepcopy(m.a_dict()) for m in self._movimientos]
            recientes = (
                movs[-MAX_MOVIMIENTOS_INFORME:]
                if len(movs) > MAX_MOVIMIENTOS_INFORME
                else movs
            )
            return {
                "bodega": None,
                "total_productos": len(self._productos),
                "total_movimientos": len(self._movimientos),
                "valorizacion": self.valorizar(),
                "productos_bajo_minimo": self.productos_bajo_minimo(),
                "movimientos_recientes": recientes,
            }

        b = str(bodega).strip()
        movs_bodega = []
        for movimiento in self._movimientos:
            if movimiento.bodega == b or movimiento.bodega_destino == b:
                movs_bodega.append(copy.deepcopy(movimiento.a_dict()))
        recientes = (
            movs_bodega[-MAX_MOVIMIENTOS_INFORME:]
            if len(movs_bodega) > MAX_MOVIMIENTOS_INFORME
            else movs_bodega
        )
        return {
            "bodega": b,
            "total_productos": len(self._productos),
            "total_movimientos": len(movs_bodega),
            "valorizacion": self.valorizar(bodega=b),
            "productos_bajo_minimo": self.productos_bajo_minimo(),
            "movimientos_recientes": recientes,
        }

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------

    def _procesar_entrada(
        self,
        solicitud: SolicitudOperacion,
        codigo_norm: str,
        bodega_norm: str,
        cantidad_num: float,
    ):
        if cantidad_num <= 0:
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_CANTIDAD_MAYOR_CERO,
            )

        try:
            costo_num = float(solicitud.costo)
        except (TypeError, ValueError):
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_COSTO_NUMERICO,
            )
        if costo_num < 0:
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_COSTO_NEGATIVO,
            )

        if codigo_norm not in self._productos:
            error = self._crear_producto_nuevo(
                codigo_norm, solicitud, bodega_norm
            )
            if error is not None:
                return error

        prod = self._productos[codigo_norm]
        stock_bodega_antes = prod.stock_en_bodega(bodega_norm)
        stock_total_antes = prod.stock_total()
        nuevo_costo = self._calcular_costo_promedio_entrada(
            prod, stock_total_antes, cantidad_num, costo_num
        )

        prod.costo_promedio = nuevo_costo
        prod.stock_por_bodega[bodega_norm] = stock_bodega_antes + cantidad_num
        stock_res = prod.stock_en_bodega(bodega_norm)

        self._registrar_movimiento(
            tipo=TIPO_ENTRADA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            bodega_destino="",
            cantidad=cantidad_num,
            costo=costo_num,
            costo_promedio_resultante=nuevo_costo,
            stock_resultante=stock_res,
            solicitud=solicitud,
        )

        return self._respuesta_exito(
            tipo=TIPO_ENTRADA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            stock=stock_res,
            stock_destino=None,
            costo_promedio=nuevo_costo,
            alerta=prod.bajo_minimo(),
            mensaje=MSG_ENTRADA_OK.format(
                codigo=codigo_norm,
                bodega=bodega_norm,
                stock=self._fmt_num(stock_res),
            ),
        )

    def _procesar_salida(
        self,
        solicitud: SolicitudOperacion,
        codigo_norm: str,
        bodega_norm: str,
        cantidad_num: float,
    ):
        if cantidad_num <= 0:
            return self._respuesta_error(
                TIPO_SALIDA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_CANTIDAD_MAYOR_CERO,
            )

        error = self._requiere_producto_existente(
            TIPO_SALIDA, codigo_norm, bodega_norm, solicitud.bodega_destino
        )
        if error is not None:
            return error

        prod = self._productos[codigo_norm]
        disponible = prod.stock_en_bodega(bodega_norm)
        if (not solicitud.forzar) and cantidad_num > disponible:
            return self._respuesta_error(
                TIPO_SALIDA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_STOCK_INSUFICIENTE.format(
                    codigo=codigo_norm,
                    bodega=bodega_norm,
                    disponible=self._fmt_num(disponible),
                    solicitado=self._fmt_num(cantidad_num),
                ),
            )

        costo_actual = float(prod.costo_promedio)
        prod.stock_por_bodega[bodega_norm] = disponible - cantidad_num
        stock_res = prod.stock_en_bodega(bodega_norm)

        self._registrar_movimiento(
            tipo=TIPO_SALIDA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            bodega_destino="",
            cantidad=cantidad_num,
            costo=costo_actual,
            costo_promedio_resultante=costo_actual,
            stock_resultante=stock_res,
            solicitud=solicitud,
        )

        return self._respuesta_exito(
            tipo=TIPO_SALIDA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            stock=stock_res,
            stock_destino=None,
            costo_promedio=costo_actual,
            alerta=prod.bajo_minimo(),
            mensaje=MSG_SALIDA_OK.format(
                codigo=codigo_norm,
                bodega=bodega_norm,
                stock=self._fmt_num(stock_res),
            ),
        )

    def _procesar_ajuste(
        self,
        solicitud: SolicitudOperacion,
        codigo_norm: str,
        bodega_norm: str,
        cantidad_num: float,
    ):
        error = self._requiere_producto_existente(
            TIPO_AJUSTE, codigo_norm, bodega_norm, solicitud.bodega_destino
        )
        if error is not None:
            return error

        if cantidad_num < 0 and not solicitud.forzar:
            return self._respuesta_error(
                TIPO_AJUSTE,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_AJUSTE_NEGATIVO,
            )

        prod = self._productos[codigo_norm]
        costo_actual = float(prod.costo_promedio)
        prod.stock_por_bodega[bodega_norm] = cantidad_num
        stock_res = prod.stock_en_bodega(bodega_norm)

        self._registrar_movimiento(
            tipo=TIPO_AJUSTE,
            codigo=codigo_norm,
            bodega=bodega_norm,
            bodega_destino="",
            cantidad=cantidad_num,
            costo=costo_actual,
            costo_promedio_resultante=costo_actual,
            stock_resultante=stock_res,
            solicitud=solicitud,
        )

        return self._respuesta_exito(
            tipo=TIPO_AJUSTE,
            codigo=codigo_norm,
            bodega=bodega_norm,
            stock=stock_res,
            stock_destino=None,
            costo_promedio=costo_actual,
            alerta=prod.bajo_minimo(),
            mensaje=MSG_AJUSTE_OK.format(
                codigo=codigo_norm,
                bodega=bodega_norm,
                stock=self._fmt_num(stock_res),
            ),
        )

    def _procesar_transferencia(
        self,
        solicitud: SolicitudOperacion,
        codigo_norm: str,
        bodega_norm: str,
        cantidad_num: float,
    ):
        if cantidad_num <= 0:
            return self._respuesta_error(
                TIPO_TRANSFERENCIA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_CANTIDAD_MAYOR_CERO,
            )

        if solicitud.bodega_destino is None or (
            isinstance(solicitud.bodega_destino, str)
            and solicitud.bodega_destino.strip() == ""
        ):
            return self._respuesta_error(
                TIPO_TRANSFERENCIA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_BODEGA_DESTINO_OBLIGATORIA,
            )

        destino_norm = str(solicitud.bodega_destino).strip()
        if destino_norm == bodega_norm:
            return self._respuesta_error(
                TIPO_TRANSFERENCIA,
                codigo_norm,
                bodega_norm,
                destino_norm,
                MSG_BODEGAS_DISTINTAS,
            )

        error = self._requiere_producto_existente(
            TIPO_TRANSFERENCIA, codigo_norm, bodega_norm, destino_norm
        )
        if error is not None:
            return error

        prod = self._productos[codigo_norm]
        disponible = prod.stock_en_bodega(bodega_norm)
        if (not solicitud.forzar) and cantidad_num > disponible:
            return self._respuesta_error(
                TIPO_TRANSFERENCIA,
                codigo_norm,
                bodega_norm,
                destino_norm,
                MSG_STOCK_INSUFICIENTE.format(
                    codigo=codigo_norm,
                    bodega=bodega_norm,
                    disponible=self._fmt_num(disponible),
                    solicitado=self._fmt_num(cantidad_num),
                ),
            )

        costo_actual = float(prod.costo_promedio)
        prod.stock_por_bodega[bodega_norm] = disponible - cantidad_num
        dest_antes = prod.stock_en_bodega(destino_norm)
        prod.stock_por_bodega[destino_norm] = dest_antes + cantidad_num
        stock_origen = prod.stock_en_bodega(bodega_norm)
        stock_destino = prod.stock_en_bodega(destino_norm)

        self._registrar_movimiento(
            tipo=TIPO_TRANSFERENCIA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            bodega_destino=destino_norm,
            cantidad=cantidad_num,
            costo=costo_actual,
            costo_promedio_resultante=costo_actual,
            stock_resultante=stock_origen,
            solicitud=solicitud,
            stock_destino_resultante=stock_destino,
        )

        return self._respuesta_exito(
            tipo=TIPO_TRANSFERENCIA,
            codigo=codigo_norm,
            bodega=bodega_norm,
            bodega_destino=destino_norm,
            stock=stock_origen,
            stock_destino=stock_destino,
            costo_promedio=costo_actual,
            alerta=prod.bajo_minimo(),
            mensaje=MSG_TRANSFERENCIA_OK.format(
                codigo=codigo_norm,
                bodega=bodega_norm,
                destino=destino_norm,
                stock_origen=self._fmt_num(stock_origen),
                stock_destino=self._fmt_num(stock_destino),
            ),
        )

    # ------------------------------------------------------------------
    # Validación y helpers de dominio
    # ------------------------------------------------------------------

    def _validar_comunes(self, solicitud: SolicitudOperacion):
        if solicitud.tipo is None or (
            isinstance(solicitud.tipo, str) and solicitud.tipo.strip() == ""
        ):
            return self._respuesta_error(
                solicitud.tipo,
                solicitud.codigo,
                solicitud.bodega,
                solicitud.bodega_destino,
                MSG_TIPO_OBLIGATORIO,
            )

        tipo_norm = str(solicitud.tipo).strip().upper()

        if solicitud.codigo is None or (
            isinstance(solicitud.codigo, str) and str(solicitud.codigo).strip() == ""
        ):
            return self._respuesta_error(
                tipo_norm,
                solicitud.codigo,
                solicitud.bodega,
                solicitud.bodega_destino,
                MSG_CODIGO_OBLIGATORIO,
            )

        if not isinstance(solicitud.forzar, bool):
            codigo_norm = self._normalizar_codigo(solicitud.codigo)
            return self._respuesta_error(
                tipo_norm,
                codigo_norm,
                solicitud.bodega,
                solicitud.bodega_destino,
                MSG_FORZAR_BOOL,
            )

        if solicitud.bodega is None or (
            isinstance(solicitud.bodega, str) and solicitud.bodega.strip() == ""
        ):
            codigo_norm = self._normalizar_codigo(solicitud.codigo)
            return self._respuesta_error(
                tipo_norm,
                codigo_norm,
                solicitud.bodega,
                solicitud.bodega_destino,
                MSG_BODEGA_OBLIGATORIA,
            )

        try:
            float(solicitud.cantidad)
        except (TypeError, ValueError):
            codigo_norm = self._normalizar_codigo(solicitud.codigo)
            bodega_norm = self._normalizar_bodega(solicitud.bodega)
            return self._respuesta_error(
                tipo_norm,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_CANTIDAD_NUMERICA,
            )

        return None

    def _crear_producto_nuevo(
        self,
        codigo_norm: str,
        solicitud: SolicitudOperacion,
        bodega_norm: str,
    ):
        if solicitud.nombre is None or str(solicitud.nombre).strip() == "":
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_NOMBRE_OBLIGATORIO,
            )

        try:
            stock_min_num = float(solicitud.stock_minimo)
        except (TypeError, ValueError):
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_STOCK_MINIMO_NUMERICO,
            )
        if stock_min_num < 0:
            return self._respuesta_error(
                TIPO_ENTRADA,
                codigo_norm,
                bodega_norm,
                solicitud.bodega_destino,
                MSG_STOCK_MINIMO_NEGATIVO,
            )

        categoria = (
            str(solicitud.categoria).strip().upper()
            if solicitud.categoria is not None
            else ""
        )
        if categoria == "":
            categoria = CATEGORIA_POR_DEFECTO

        self._productos[codigo_norm] = Producto(
            nombre=str(solicitud.nombre).strip(),
            categoria=categoria,
            costo_promedio=0.0,
            stock_minimo=stock_min_num,
            stock_por_bodega={},
        )
        return None

    def _calcular_costo_promedio_entrada(
        self,
        prod: Producto,
        stock_total_antes: float,
        cantidad_num: float,
        costo_num: float,
    ) -> float:
        nuevo_total = stock_total_antes + cantidad_num
        if nuevo_total == 0:
            return float(prod.costo_promedio)
        nuevo_costo = (
            stock_total_antes * float(prod.costo_promedio) + cantidad_num * costo_num
        ) / nuevo_total
        return round(nuevo_costo, 2)

    def _requiere_producto_existente(
        self, tipo: str, codigo_norm: str, bodega_norm: str, bodega_destino
    ):
        if codigo_norm not in self._productos:
            return self._respuesta_error(
                tipo,
                codigo_norm,
                bodega_norm,
                bodega_destino,
                MSG_PRODUCTO_NO_EXISTE.format(codigo=codigo_norm),
            )
        return None

    def _registrar_movimiento(
        self,
        tipo: str,
        codigo: str,
        bodega: str,
        bodega_destino: str,
        cantidad: float,
        costo: float,
        costo_promedio_resultante: float,
        stock_resultante: float,
        solicitud: SolicitudOperacion,
        stock_destino_resultante: Optional[float] = None,
    ):
        self._contador_movimientos += 1
        fecha_mov = (
            solicitud.fecha if solicitud.fecha is not None else self._reloj()
        )
        movimiento = Movimiento(
            id=self._contador_movimientos,
            tipo=tipo,
            codigo=codigo,
            bodega=bodega,
            bodega_destino=bodega_destino,
            cantidad=cantidad,
            costo=costo,
            costo_promedio_resultante=costo_promedio_resultante,
            stock_resultante=stock_resultante,
            responsable=str(solicitud.responsable)
            if solicitud.responsable is not None
            else "",
            motivo=str(solicitud.motivo) if solicitud.motivo is not None else "",
            cliente=str(solicitud.cliente) if solicitud.cliente is not None else "",
            fecha=fecha_mov,
            stock_destino_resultante=stock_destino_resultante,
        )
        self._movimientos.append(movimiento)

    def _producto_a_dict(self, prod: Producto) -> Dict[str, Any]:
        return {
            "nombre": prod.nombre,
            "categoria": prod.categoria,
            "costo_promedio": prod.costo_promedio,
            "stock_minimo": prod.stock_minimo,
            "stock_por_bodega": dict(prod.stock_por_bodega),
            "stock_total": prod.stock_total(),
        }

    @staticmethod
    def _normalizar_codigo(codigo) -> str:
        if codigo is None or str(codigo).strip() == "":
            return ""
        return str(codigo).strip().upper().replace(" ", "")

    @staticmethod
    def _normalizar_bodega(bodega) -> str:
        if bodega is None:
            return ""
        return str(bodega).strip()

    def _respuesta_exito(
        self,
        tipo: str,
        codigo: str,
        bodega: str,
        stock: float,
        stock_destino,
        costo_promedio: float,
        alerta: bool,
        mensaje: str,
        bodega_destino: str = "",
    ):
        return {
            "ok": True,
            "tipo": tipo,
            "codigo": codigo,
            "bodega": bodega,
            "bodega_destino": bodega_destino,
            "stock": stock,
            "stock_destino": stock_destino,
            "costo_promedio": costo_promedio,
            "alerta_minimo": alerta,
            "mensaje": mensaje,
        }

    def _respuesta_error(self, tipo, codigo, bodega, bodega_destino, mensaje):
        tipo_out = ""
        if tipo is not None:
            tipo_out = str(tipo).strip().upper() if str(tipo).strip() else ""

        cod_out = ""
        if codigo is not None and str(codigo).strip() != "":
            cod_out = str(codigo).strip().upper().replace(" ", "")

        bod_out = ""
        if bodega is not None:
            bod_out = str(bodega).strip()

        dest_out = ""
        if bodega_destino is not None:
            dest_out = str(bodega_destino).strip()

        return {
            "ok": False,
            "tipo": tipo_out,
            "codigo": cod_out,
            "bodega": bod_out,
            "bodega_destino": dest_out,
            "stock": None,
            "stock_destino": None,
            "costo_promedio": None,
            "alerta_minimo": False,
            "mensaje": mensaje,
        }

    @staticmethod
    def _fmt_num(n):
        if isinstance(n, float) and n == int(n):
            return str(int(n))
        s = str(n)
        if "e" in s or "E" in s:
            return s
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
