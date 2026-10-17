# -*- coding: utf-8 -*-
"""
Sistema de gestión de inventario — versión inicial con deuda técnica deliberada.
Módulo seleccionado para el estudio de caso de Mantenimiento de Sistemas de Software.
"""

from __future__ import annotations

import copy
import datetime
import json  # código muerto: nunca se usa
import math  # código muerto: nunca se usa
import os  # código muerto: nunca se usa
import random  # código muerto: nunca se usa
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Funciones muertas (dead code) — nadie las invoca desde la API pública
# ---------------------------------------------------------------------------

def calcular_iva_colombiano(valor_base, tarifa=0.19):
    """Calcula el IVA colombiano. No se usa en el flujo de inventario."""
    if valor_base is None:
        return 0
    try:
        base = float(valor_base)
    except (TypeError, ValueError):
        return 0
    if base < 0:
        base = abs(base)
    iva = base * float(tarifa)
    total = base + iva
    detalle = {
        "base": round(base, 2),
        "tarifa": tarifa,
        "iva": round(iva, 2),
        "total": round(total, 2),
    }
    # Complejidad innecesaria sin consumidores
    if tarifa > 0.5:
        detalle["alerta"] = "tarifa_alta"
    elif tarifa < 0:
        detalle["alerta"] = "tarifa_negativa"
    else:
        detalle["alerta"] = "ok"
    return detalle


def aplicar_descuento_por_volumen(cantidad, precio_unitario, umbral=100, porcentaje=0.05):
    """Aplica un descuento por volumen. Código muerto."""
    try:
        cant = float(cantidad)
        precio = float(precio_unitario)
    except (TypeError, ValueError):
        return {"subtotal": 0, "descuento": 0, "total": 0}
    subtotal = cant * precio
    if cant >= umbral:
        descuento = subtotal * porcentaje
    else:
        descuento = 0
    return {
        "subtotal": round(subtotal, 2),
        "descuento": round(descuento, 2),
        "total": round(subtotal - descuento, 2),
        "aplicado": descuento > 0,
    }


def _formatear_moneda_fantasma(valor):
    """Helper muerto para formato de moneda."""
    try:
        return "$ {:,.2f}".format(float(valor))
    except (TypeError, ValueError):
        return "$ 0.00"


def _normalizar_texto_legacy(texto):
    """Normalización legacy sin uso en el flujo principal."""
    if texto is None:
        return ""
    t = str(texto).strip().upper()
    for ch in ["á", "é", "í", "ó", "ú"]:
        t = t.replace(ch.upper(), ch.upper())
    return t


class SistemaGestionInventario:
    """
    Inventario monolítico con deuda técnica:
    - Un único método enorme concentra ENTRADA, SALIDA, AJUSTE y TRANSFERENCIA.
    - Diccionarios en lugar de objetos de dominio.
    - Armado duplicado de movimientos.
    - Lista larga de parámetros.
    - Atributos que se escriben y no se leen.
    """

    def __init__(self, reloj=None):
        self._reloj = reloj if reloj is not None else datetime.datetime.now
        # productos[codigo] = dict con nombre, categoria, costo_promedio, stock_minimo, stock_por_bodega
        self._productos: Dict[str, Dict[str, Any]] = {}
        self._movimientos: List[Dict[str, Any]] = []
        self._contador_movimientos = 0
        # Atributos escritos y nunca leídos (deuda)
        self._ultima_auditoria_interna = None
        self._buffer_metricas_fantasma = []
        self._flag_modo_debug_legacy = False
        self._cache_valorizacion_obsoleta = None
        self._historial_responsables_sin_uso = []

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
        """
        Método excesivamente largo: valida, crea producto, ejecuta las cuatro
        operaciones y arma movimientos con lógica duplicada.
        """
        # --- métricas fantasma (escritas, no leídas) ---
        self._ultima_auditoria_interna = {
            "tipo": tipo,
            "codigo": codigo,
            "ts": self._reloj(),
        }
        self._buffer_metricas_fantasma.append(len(self._movimientos))
        if responsable:
            self._historial_responsables_sin_uso.append(str(responsable))
        self._flag_modo_debug_legacy = bool(motivo) and bool(cliente)

        # --- validación de tipo ---
        if tipo is None or (isinstance(tipo, str) and tipo.strip() == ""):
            return self._respuesta_error(
                tipo, codigo, bodega, bodega_destino, "El tipo de operación es obligatorio."
            )

        tipo_norm = str(tipo).strip().upper()
        codigo_raw = codigo

        # --- validación de código ---
        if codigo_raw is None or (isinstance(codigo_raw, str) and str(codigo_raw).strip() == ""):
            return self._respuesta_error(
                tipo_norm, codigo_raw, bodega, bodega_destino, "El código del producto es obligatorio."
            )
        codigo_norm = str(codigo_raw).strip().upper().replace(" ", "")

        # --- forzar debe ser bool ---
        if not isinstance(forzar, bool):
            return self._respuesta_error(
                tipo_norm,
                codigo_norm,
                bodega,
                bodega_destino,
                "El indicador forzar debe ser verdadero o falso.",
            )

        # --- bodega origen ---
        if bodega is None or (isinstance(bodega, str) and bodega.strip() == ""):
            return self._respuesta_error(
                tipo_norm, codigo_norm, bodega, bodega_destino, "La bodega es obligatoria."
            )
        bodega_norm = str(bodega).strip()  # se conserva la caja

        # --- cantidad numérica ---
        try:
            cantidad_num = float(cantidad)
        except (TypeError, ValueError):
            return self._respuesta_error(
                tipo_norm, codigo_norm, bodega_norm, bodega_destino, "La cantidad debe ser numérica."
            )

        # =====================================================================
        # RAMA: ENTRADA
        # =====================================================================
        if tipo_norm == "ENTRADA":
            if cantidad_num <= 0:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "La cantidad debe ser mayor que cero.",
                )
            try:
                costo_num = float(costo)
            except (TypeError, ValueError):
                return self._respuesta_error(
                    tipo_norm, codigo_norm, bodega_norm, bodega_destino, "El costo debe ser numérico."
                )
            if costo_num < 0:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "El costo no puede ser negativo.",
                )

            if codigo_norm not in self._productos:
                if nombre is None or str(nombre).strip() == "":
                    return self._respuesta_error(
                        tipo_norm,
                        codigo_norm,
                        bodega_norm,
                        bodega_destino,
                        "El nombre es obligatorio para registrar un producto nuevo.",
                    )
                try:
                    stock_min_num = float(stock_minimo)
                except (TypeError, ValueError):
                    return self._respuesta_error(
                        tipo_norm,
                        codigo_norm,
                        bodega_norm,
                        bodega_destino,
                        "El stock mínimo debe ser numérico.",
                    )
                if stock_min_num < 0:
                    return self._respuesta_error(
                        tipo_norm,
                        codigo_norm,
                        bodega_norm,
                        bodega_destino,
                        "El stock mínimo no puede ser negativo.",
                    )
                cat = str(categoria).strip().upper() if categoria is not None else ""
                if cat == "":
                    cat = "GENERAL"
                self._productos[codigo_norm] = {
                    "nombre": str(nombre).strip(),
                    "categoria": cat,
                    "costo_promedio": 0.0,
                    "stock_minimo": stock_min_num,
                    "stock_por_bodega": {},
                }

            prod = self._productos[codigo_norm]
            # segunda entrada: no cambia nombre, categoria ni stock_minimo
            stock_bodega_antes = float(prod["stock_por_bodega"].get(bodega_norm, 0))
            stock_total_antes = sum(float(v) for v in prod["stock_por_bodega"].values())

            # costo promedio ponderado
            nuevo_total = stock_total_antes + cantidad_num
            if nuevo_total == 0:
                # conservar costo anterior
                nuevo_costo = float(prod["costo_promedio"])
            else:
                nuevo_costo = (
                    stock_total_antes * float(prod["costo_promedio"]) + cantidad_num * costo_num
                ) / nuevo_total
                nuevo_costo = round(nuevo_costo, 2)

            prod["costo_promedio"] = nuevo_costo
            prod["stock_por_bodega"][bodega_norm] = stock_bodega_antes + cantidad_num
            stock_res = float(prod["stock_por_bodega"][bodega_norm])

            # armado duplicado de movimiento (ENTRADA)
            self._contador_movimientos += 1
            fecha_mov = fecha if fecha is not None else self._reloj()
            movimiento = {
                "id": self._contador_movimientos,
                "tipo": "ENTRADA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "cantidad": cantidad_num,
                "costo": costo_num,
                "costo_promedio_resultante": nuevo_costo,
                "stock_resultante": stock_res,
                "responsable": str(responsable) if responsable is not None else "",
                "motivo": str(motivo) if motivo is not None else "",
                "cliente": str(cliente) if cliente is not None else "",
                "fecha": fecha_mov,
            }
            self._movimientos.append(movimiento)
            self._cache_valorizacion_obsoleta = None

            stock_total = sum(float(v) for v in prod["stock_por_bodega"].values())
            alerta = stock_total < float(prod["stock_minimo"])
            msg = (
                "Entrada registrada para "
                + codigo_norm
                + " en "
                + bodega_norm
                + ". Stock resultante: "
                + self._fmt_num(stock_res)
                + "."
            )
            return {
                "ok": True,
                "tipo": "ENTRADA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "stock": stock_res,
                "stock_destino": None,
                "costo_promedio": nuevo_costo,
                "alerta_minimo": alerta,
                "mensaje": msg,
            }

        # =====================================================================
        # RAMA: SALIDA
        # =====================================================================
        elif tipo_norm == "SALIDA":
            if cantidad_num <= 0:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "La cantidad debe ser mayor que cero.",
                )
            if codigo_norm not in self._productos:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "El producto " + codigo_norm + " no existe en el inventario.",
                )
            prod = self._productos[codigo_norm]
            disponible = float(prod["stock_por_bodega"].get(bodega_norm, 0))
            if (not forzar) and cantidad_num > disponible:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "Stock insuficiente para "
                    + codigo_norm
                    + " en "
                    + bodega_norm
                    + ": disponible "
                    + self._fmt_num(disponible)
                    + ", solicitado "
                    + self._fmt_num(cantidad_num)
                    + ".",
                )
            # la salida no cambia el costo
            costo_actual = float(prod["costo_promedio"])
            prod["stock_por_bodega"][bodega_norm] = disponible - cantidad_num
            stock_res = float(prod["stock_por_bodega"][bodega_norm])

            # armado duplicado de movimiento (SALIDA)
            self._contador_movimientos += 1
            fecha_mov = fecha if fecha is not None else self._reloj()
            movimiento = {
                "id": self._contador_movimientos,
                "tipo": "SALIDA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "cantidad": cantidad_num,
                "costo": costo_actual,
                "costo_promedio_resultante": costo_actual,
                "stock_resultante": stock_res,
                "responsable": str(responsable) if responsable is not None else "",
                "motivo": str(motivo) if motivo is not None else "",
                "cliente": str(cliente) if cliente is not None else "",
                "fecha": fecha_mov,
            }
            self._movimientos.append(movimiento)
            self._cache_valorizacion_obsoleta = None

            stock_total = sum(float(v) for v in prod["stock_por_bodega"].values())
            alerta = stock_total < float(prod["stock_minimo"])
            msg = (
                "Salida registrada para "
                + codigo_norm
                + " en "
                + bodega_norm
                + ". Stock resultante: "
                + self._fmt_num(stock_res)
                + "."
            )
            return {
                "ok": True,
                "tipo": "SALIDA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "stock": stock_res,
                "stock_destino": None,
                "costo_promedio": costo_actual,
                "alerta_minimo": alerta,
                "mensaje": msg,
            }

        # =====================================================================
        # RAMA: AJUSTE
        # =====================================================================
        elif tipo_norm == "AJUSTE":
            # cantidad ajustada no puede ser negativa (el stock resultante)
            # En AJUSTE, cantidad representa el nuevo stock absoluto en la bodega
            if codigo_norm not in self._productos:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "El producto " + codigo_norm + " no existe en el inventario.",
                )
            # Para AJUSTE: cantidad es el stock objetivo; no exige > 0 como ENTRADA/SALIDA
            # pero no puede ser negativa salvo forzar... Spec: "La cantidad ajustada no puede ser negativa."
            if cantidad_num < 0 and not forzar:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "La cantidad ajustada no puede ser negativa.",
                )
            if cantidad_num < 0 and forzar:
                # permite stock negativo
                pass
            # Si cantidad_num >= 0, ok even without forzar

            prod = self._productos[codigo_norm]
            # el ajuste no cambia el costo
            costo_actual = float(prod["costo_promedio"])
            prod["stock_por_bodega"][bodega_norm] = cantidad_num
            stock_res = float(prod["stock_por_bodega"][bodega_norm])

            # armado duplicado de movimiento (AJUSTE)
            self._contador_movimientos += 1
            fecha_mov = fecha if fecha is not None else self._reloj()
            movimiento = {
                "id": self._contador_movimientos,
                "tipo": "AJUSTE",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "cantidad": cantidad_num,
                "costo": costo_actual,
                "costo_promedio_resultante": costo_actual,
                "stock_resultante": stock_res,
                "responsable": str(responsable) if responsable is not None else "",
                "motivo": str(motivo) if motivo is not None else "",
                "cliente": str(cliente) if cliente is not None else "",
                "fecha": fecha_mov,
            }
            self._movimientos.append(movimiento)
            self._cache_valorizacion_obsoleta = None

            stock_total = sum(float(v) for v in prod["stock_por_bodega"].values())
            alerta = stock_total < float(prod["stock_minimo"])
            msg = (
                "Ajuste registrado para "
                + codigo_norm
                + " en "
                + bodega_norm
                + ". Stock resultante: "
                + self._fmt_num(stock_res)
                + "."
            )
            return {
                "ok": True,
                "tipo": "AJUSTE",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": "",
                "stock": stock_res,
                "stock_destino": None,
                "costo_promedio": costo_actual,
                "alerta_minimo": alerta,
                "mensaje": msg,
            }

        # =====================================================================
        # RAMA: TRANSFERENCIA
        # =====================================================================
        elif tipo_norm == "TRANSFERENCIA":
            if cantidad_num <= 0:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "La cantidad debe ser mayor que cero.",
                )
            if bodega_destino is None or (
                isinstance(bodega_destino, str) and bodega_destino.strip() == ""
            ):
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    bodega_destino,
                    "La bodega de destino es obligatoria.",
                )
            destino_norm = str(bodega_destino).strip()
            if destino_norm == bodega_norm:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    destino_norm,
                    "La bodega de origen y destino deben ser distintas.",
                )
            if codigo_norm not in self._productos:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    destino_norm,
                    "El producto " + codigo_norm + " no existe en el inventario.",
                )
            prod = self._productos[codigo_norm]
            disponible = float(prod["stock_por_bodega"].get(bodega_norm, 0))
            if (not forzar) and cantidad_num > disponible:
                return self._respuesta_error(
                    tipo_norm,
                    codigo_norm,
                    bodega_norm,
                    destino_norm,
                    "Stock insuficiente para "
                    + codigo_norm
                    + " en "
                    + bodega_norm
                    + ": disponible "
                    + self._fmt_num(disponible)
                    + ", solicitado "
                    + self._fmt_num(cantidad_num)
                    + ".",
                )
            # transferencia no cambia el costo
            costo_actual = float(prod["costo_promedio"])
            prod["stock_por_bodega"][bodega_norm] = disponible - cantidad_num
            dest_antes = float(prod["stock_por_bodega"].get(destino_norm, 0))
            prod["stock_por_bodega"][destino_norm] = dest_antes + cantidad_num
            stock_origen = float(prod["stock_por_bodega"][bodega_norm])
            stock_destino = float(prod["stock_por_bodega"][destino_norm])

            # armado duplicado de movimiento (TRANSFERENCIA)
            self._contador_movimientos += 1
            fecha_mov = fecha if fecha is not None else self._reloj()
            movimiento = {
                "id": self._contador_movimientos,
                "tipo": "TRANSFERENCIA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": destino_norm,
                "cantidad": cantidad_num,
                "costo": costo_actual,
                "costo_promedio_resultante": costo_actual,
                "stock_resultante": stock_origen,
                "stock_destino_resultante": stock_destino,
                "responsable": str(responsable) if responsable is not None else "",
                "motivo": str(motivo) if motivo is not None else "",
                "cliente": str(cliente) if cliente is not None else "",
                "fecha": fecha_mov,
            }
            self._movimientos.append(movimiento)
            self._cache_valorizacion_obsoleta = None

            stock_total = sum(float(v) for v in prod["stock_por_bodega"].values())
            alerta = stock_total < float(prod["stock_minimo"])
            msg = (
                "Transferencia registrada para "
                + codigo_norm
                + " desde "
                + bodega_norm
                + " hacia "
                + destino_norm
                + ". Stock origen: "
                + self._fmt_num(stock_origen)
                + ". Stock destino: "
                + self._fmt_num(stock_destino)
                + "."
            )
            return {
                "ok": True,
                "tipo": "TRANSFERENCIA",
                "codigo": codigo_norm,
                "bodega": bodega_norm,
                "bodega_destino": destino_norm,
                "stock": stock_origen,
                "stock_destino": stock_destino,
                "costo_promedio": costo_actual,
                "alerta_minimo": alerta,
                "mensaje": msg,
            }

        else:
            return self._respuesta_error(
                tipo_norm,
                codigo_norm,
                bodega_norm,
                bodega_destino,
                "Tipo de operación no soportado: " + tipo_norm + ".",
            )

    # ------------------------------------------------------------------
    # API de consulta (devuelve copias)
    # ------------------------------------------------------------------

    def consultar_stock(self, codigo=None, bodega=None):
        """Consulta stock. Si codigo es None, retorna todo. Copias."""
        if codigo is None:
            resultado = {}
            for cod, prod in self._productos.items():
                resultado[cod] = {
                    "nombre": prod["nombre"],
                    "categoria": prod["categoria"],
                    "costo_promedio": prod["costo_promedio"],
                    "stock_minimo": prod["stock_minimo"],
                    "stock_por_bodega": dict(prod["stock_por_bodega"]),
                    "stock_total": sum(float(v) for v in prod["stock_por_bodega"].values()),
                }
            return resultado
        cod = str(codigo).strip().upper().replace(" ", "")
        if cod not in self._productos:
            return None
        prod = self._productos[cod]
        if bodega is not None:
            b = str(bodega).strip()
            return float(prod["stock_por_bodega"].get(b, 0))
        return {
            "nombre": prod["nombre"],
            "categoria": prod["categoria"],
            "costo_promedio": prod["costo_promedio"],
            "stock_minimo": prod["stock_minimo"],
            "stock_por_bodega": dict(prod["stock_por_bodega"]),
            "stock_total": sum(float(v) for v in prod["stock_por_bodega"].values()),
        }

    def valorizar(self, bodega=None):
        """Valoriza inventario = sum(stock * costo_promedio). Copia/agregado."""
        total = 0.0
        detalle = []
        for cod, prod in self._productos.items():
            if bodega is None:
                stock = sum(float(v) for v in prod["stock_por_bodega"].values())
            else:
                b = str(bodega).strip()
                stock = float(prod["stock_por_bodega"].get(b, 0))
            valor = stock * float(prod["costo_promedio"])
            total += valor
            detalle.append(
                {
                    "codigo": cod,
                    "nombre": prod["nombre"],
                    "stock": stock,
                    "costo_promedio": prod["costo_promedio"],
                    "valor": round(valor, 2),
                }
            )
        return {"total": round(total, 2), "detalle": detalle}

    def productos_bajo_minimo(self):
        """Lista productos cuyo stock total está bajo el mínimo. Copias."""
        bajo = []
        for cod, prod in self._productos.items():
            stock_total = sum(float(v) for v in prod["stock_por_bodega"].values())
            if stock_total < float(prod["stock_minimo"]):
                bajo.append(
                    {
                        "codigo": cod,
                        "nombre": prod["nombre"],
                        "stock_total": stock_total,
                        "stock_minimo": prod["stock_minimo"],
                        "faltante": float(prod["stock_minimo"]) - stock_total,
                    }
                )
        return bajo

    def obtener_movimientos(self, codigo=None, bodega=None):
        """Devuelve copia de movimientos, opcionalmente filtrados."""
        movs = []
        for m in self._movimientos:
            if codigo is not None:
                cod = str(codigo).strip().upper().replace(" ", "")
                if m["codigo"] != cod:
                    continue
            if bodega is not None:
                b = str(bodega).strip()
                if m["bodega"] != b and m.get("bodega_destino", "") != b:
                    continue
            movs.append(copy.deepcopy(m))
        return movs

    def generar_informe_operativo(self, bodega=None):
        """
        Informe operativo. Si se indica bodega, incluye solo los 10
        movimientos más recientes de esa bodega.
        """
        if bodega is None:
            movs = [copy.deepcopy(m) for m in self._movimientos]
            valorizacion = self.valorizar()
            bajo = self.productos_bajo_minimo()
            return {
                "bodega": None,
                "total_productos": len(self._productos),
                "total_movimientos": len(self._movimientos),
                "valorizacion": valorizacion,
                "productos_bajo_minimo": bajo,
                "movimientos_recientes": movs[-10:] if len(movs) > 10 else movs,
            }
        b = str(bodega).strip()
        movs_bodega = []
        for m in self._movimientos:
            if m["bodega"] == b or m.get("bodega_destino", "") == b:
                movs_bodega.append(copy.deepcopy(m))
        # 10 más recientes
        recientes = movs_bodega[-10:] if len(movs_bodega) > 10 else movs_bodega
        valorizacion = self.valorizar(bodega=b)
        bajo = self.productos_bajo_minimo()
        return {
            "bodega": b,
            "total_productos": len(self._productos),
            "total_movimientos": len(movs_bodega),
            "valorizacion": valorizacion,
            "productos_bajo_minimo": bajo,
            "movimientos_recientes": recientes,
        }

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _fmt_num(self, n):
        """Formatea número: entero sin decimales si es .0, si no con representación natural."""
        if isinstance(n, float) and n == int(n):
            return str(int(n))
        # Evitar 10.0 -> mostrar 10; para 10.5 mostrar 10.5
        s = str(n)
        if "e" in s or "E" in s:
            return s
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

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


# Bloque de demostración local (no afecta importación)
if __name__ == "__main__":
    inv = SistemaGestionInventario(reloj=lambda: datetime.datetime(2026, 10, 17, 12, 0, 0))
    print(inv.procesar_operacion_completa(
        "entrada", "abc 1", nombre="Tornillo", categoria="ferreteria",
        costo=100, cantidad=10, stock_minimo=5, bodega="Central",
    ))
    print(inv.consultar_stock("ABC1"))
    print(calcular_iva_colombiano(1000))  # solo demo del dead code
