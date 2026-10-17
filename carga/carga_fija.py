# -*- coding: utf-8 -*-
"""
Carga fija reproducible. El checksum SHA-256 del resultado debe ser idéntico
antes y después de la refactorización (comportamiento observable invariante).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gestion_inventario import SistemaGestionInventario


def reloj():
    return datetime.datetime(2026, 10, 17, 8, 0, 0)


def ejecutar_carga():
    inv = SistemaGestionInventario(reloj=reloj)
    ops = []

    ops.append(inv.procesar_operacion_completa(
        "entrada", "sku 01", nombre="Tornillo M6", categoria="ferreteria",
        costo=120.5, cantidad=100, stock_minimo=20, bodega="Bogota",
        responsable="Ana",
    ))
    ops.append(inv.procesar_operacion_completa(
        "ENTRADA", "SKU01", nombre="IGNORAR", categoria="OTRA",
        costo=80, cantidad=50, stock_minimo=999, bodega="Bogota",
    ))
    ops.append(inv.procesar_operacion_completa(
        "salida", "sku01", cantidad=30, bodega="Bogota", cliente="Acme",
    ))
    ops.append(inv.procesar_operacion_completa(
        "transferencia", "SKU01", cantidad=40, bodega="Bogota",
        bodega_destino="Medellin", responsable="Luis",
    ))
    ops.append(inv.procesar_operacion_completa(
        "ajuste", "SKU01", cantidad=25, bodega="Bogota", motivo="conteo",
    ))
    ops.append(inv.procesar_operacion_completa(
        "entrada", "sku 02", nombre="Tuerca", costo=15, cantidad=10,
        stock_minimo=50, bodega="Medellin",
    ))
    ops.append(inv.procesar_operacion_completa(
        "SALIDA", "SKU02", cantidad=8, bodega="Medellin",
    ))
    # error controlado
    ops.append(inv.procesar_operacion_completa(
        "SALIDA", "SKU02", cantidad=100, bodega="Medellin",
    ))
    ops.append(inv.procesar_operacion_completa(
        "SALIDA", "SKU01", cantidad=1000, bodega="Bogota", forzar=True,
    ))

    resultado = {
        "operaciones": ops,
        "stock_sku01": inv.consultar_stock("SKU01"),
        "stock_sku02": inv.consultar_stock("SKU02"),
        "valorizacion": inv.valorizar(),
        "bajo_minimo": inv.productos_bajo_minimo(),
        "movimientos": inv.obtener_movimientos(),
        "informe_bogota": inv.generar_informe_operativo(bodega="Bogota"),
        "informe_global": inv.generar_informe_operativo(),
    }
    return resultado


def _serializar(obj):
    def default(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        raise TypeError(type(o))

    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=default)


def checksum_de(resultado):
    payload = _serializar(resultado).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main():
    resultado = ejecutar_carga()
    digest = checksum_de(resultado)
    out = Path(__file__).resolve().parent / "resultado_carga.json"
    out.write_text(_serializar({"checksum": digest, "resultado": resultado}), encoding="utf-8")
    print(digest)
    return digest


if __name__ == "__main__":
    main()
