# -*- coding: utf-8 -*-
"""
Pruebas automatizadas del comportamiento observable de SistemaGestionInventario.
Demuestran que la refactorización no altera la API ni los resultados.
"""

from __future__ import annotations

import copy
import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gestion_inventario import SistemaGestionInventario  # noqa: E402


def reloj_fijo():
    return datetime.datetime(2026, 10, 17, 10, 0, 0)


@pytest.fixture
def inv():
    return SistemaGestionInventario(reloj=reloj_fijo)


def test_entrada_crea_producto_y_normaliza():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    r = inv.procesar_operacion_completa(
        "  entrada ",
        " ab c ",
        nombre="Tornillo",
        categoria="ferreteria",
        costo=100,
        cantidad=10,
        stock_minimo=5,
        bodega="  Central  ",
    )
    assert r["ok"] is True
    assert r["tipo"] == "ENTRADA"
    assert r["codigo"] == "ABC"
    assert r["bodega"] == "Central"
    assert r["stock"] == 10
    assert r["costo_promedio"] == 100.0
    assert r["mensaje"] == "Entrada registrada para ABC en Central. Stock resultante: 10."
    stock = inv.consultar_stock("ABC")
    assert stock["categoria"] == "FERRETERIA"
    assert stock["nombre"] == "Tornillo"


def test_categoria_vacia_queda_general():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P1", nombre="Item", categoria="", costo=10, cantidad=1,
        stock_minimo=0, bodega="A",
    )
    assert inv.consultar_stock("P1")["categoria"] == "GENERAL"


def test_segunda_entrada_no_cambia_nombre_categoria_ni_minimo():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P2", nombre="Original", categoria="CAT", costo=10,
        cantidad=5, stock_minimo=2, bodega="A",
    )
    inv.procesar_operacion_completa(
        "ENTRADA", "P2", nombre="Otro", categoria="OTRA", costo=20,
        cantidad=5, stock_minimo=99, bodega="A",
    )
    s = inv.consultar_stock("P2")
    assert s["nombre"] == "Original"
    assert s["categoria"] == "CAT"
    assert s["stock_minimo"] == 2
    # promedio ponderado: (5*10 + 5*20)/10 = 15
    assert s["costo_promedio"] == 15.0
    assert s["stock_total"] == 10


def test_costo_promedio_redondeo_dos_decimales():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P3", nombre="X", costo=10, cantidad=3, bodega="A",
    )
    inv.procesar_operacion_completa(
        "ENTRADA", "P3", nombre="X", costo=20, cantidad=1, bodega="A",
    )
    # (30 + 20)/4 = 12.5
    assert inv.consultar_stock("P3")["costo_promedio"] == 12.5


def test_salida_no_cambia_costo_y_mensaje():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P4", nombre="Y", costo=50, cantidad=10, bodega="B1",
    )
    r = inv.procesar_operacion_completa("SALIDA", "P4", cantidad=3, bodega="B1")
    assert r["ok"] is True
    assert r["stock"] == 7
    assert r["costo_promedio"] == 50.0
    assert r["mensaje"] == "Salida registrada para P4 en B1. Stock resultante: 7."


def test_stock_insuficiente_sin_forzar():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P5", nombre="Z", costo=1, cantidad=2, bodega="B",
    )
    r = inv.procesar_operacion_completa("SALIDA", "P5", cantidad=5, bodega="B")
    assert r["ok"] is False
    assert r["mensaje"] == (
        "Stock insuficiente para P5 en B: disponible 2, solicitado 5."
    )


def test_forzar_permite_stock_negativo_en_salida():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P6", nombre="Z", costo=1, cantidad=2, bodega="B",
    )
    r = inv.procesar_operacion_completa(
        "SALIDA", "P6", cantidad=5, bodega="B", forzar=True,
    )
    assert r["ok"] is True
    assert r["stock"] == -3


def test_forzar_debe_ser_bool():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    r = inv.procesar_operacion_completa(
        "ENTRADA", "P7", nombre="Z", costo=1, cantidad=1, bodega="B", forzar="si",
    )
    assert r["ok"] is False
    assert r["mensaje"] == "El indicador forzar debe ser verdadero o falso."


def test_ajuste_y_transferencia():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P8", nombre="T", costo=10, cantidad=20, bodega="Origen",
    )
    r_aj = inv.procesar_operacion_completa("AJUSTE", "P8", cantidad=15, bodega="Origen")
    assert r_aj["ok"] is True
    assert r_aj["stock"] == 15
    assert r_aj["costo_promedio"] == 10.0
    assert r_aj["mensaje"] == "Ajuste registrado para P8 en Origen. Stock resultante: 15."

    r_tr = inv.procesar_operacion_completa(
        "TRANSFERENCIA", "P8", cantidad=5, bodega="Origen", bodega_destino="Destino",
    )
    assert r_tr["ok"] is True
    assert r_tr["stock"] == 10
    assert r_tr["stock_destino"] == 5
    assert r_tr["costo_promedio"] == 10.0
    assert r_tr["mensaje"] == (
        "Transferencia registrada para P8 desde Origen hacia Destino. "
        "Stock origen: 10. Stock destino: 5."
    )


def test_ajuste_negativo_sin_forzar():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P9", nombre="T", costo=1, cantidad=5, bodega="A",
    )
    r = inv.procesar_operacion_completa("AJUSTE", "P9", cantidad=-1, bodega="A")
    assert r["ok"] is False
    assert r["mensaje"] == "La cantidad ajustada no puede ser negativa."


def test_mensajes_de_validacion():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    assert inv.procesar_operacion_completa("", "X", bodega="A")["mensaje"] == (
        "El tipo de operación es obligatorio."
    )
    assert inv.procesar_operacion_completa("FOO", "X", bodega="A")["mensaje"] == (
        "Tipo de operación no soportado: FOO."
    )
    assert inv.procesar_operacion_completa("ENTRADA", "", bodega="A")["mensaje"] == (
        "El código del producto es obligatorio."
    )
    assert inv.procesar_operacion_completa("ENTRADA", "X", bodega="")["mensaje"] == (
        "La bodega es obligatoria."
    )
    assert inv.procesar_operacion_completa(
        "ENTRADA", "X", nombre="N", cantidad="abc", bodega="A"
    )["mensaje"] == "La cantidad debe ser numérica."
    assert inv.procesar_operacion_completa(
        "ENTRADA", "X", nombre="N", cantidad=0, bodega="A"
    )["mensaje"] == "La cantidad debe ser mayor que cero."
    assert inv.procesar_operacion_completa(
        "ENTRADA", "X", nombre="N", cantidad=1, costo="x", bodega="A"
    )["mensaje"] == "El costo debe ser numérico."
    assert inv.procesar_operacion_completa(
        "ENTRADA", "X", nombre="N", cantidad=1, costo=-1, bodega="A"
    )["mensaje"] == "El costo no puede ser negativo."
    assert inv.procesar_operacion_completa(
        "ENTRADA", "X", nombre="", cantidad=1, costo=1, bodega="A"
    )["mensaje"] == "El nombre es obligatorio para registrar un producto nuevo."
    assert inv.procesar_operacion_completa(
        "SALIDA", "NOEXISTE", cantidad=1, bodega="A"
    )["mensaje"] == "El producto NOEXISTE no existe en el inventario."
    assert inv.procesar_operacion_completa(
        "TRANSFERENCIA", "X", cantidad=1, bodega="A", bodega_destino=""
    )["mensaje"] == "La bodega de destino es obligatoria."


def test_transferencia_mismas_bodegas():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P10", nombre="T", costo=1, cantidad=5, bodega="Misma",
    )
    r = inv.procesar_operacion_completa(
        "TRANSFERENCIA", "P10", cantidad=1, bodega="Misma", bodega_destino="Misma",
    )
    assert r["mensaje"] == "La bodega de origen y destino deben ser distintas."


def test_consultas_devuelven_copias():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P11", nombre="Copia", costo=10, cantidad=5, bodega="A",
    )
    s = inv.consultar_stock("P11")
    s["nombre"] = "HACKED"
    s["stock_por_bodega"]["A"] = 999
    assert inv.consultar_stock("P11")["nombre"] == "Copia"
    assert inv.consultar_stock("P11", bodega="A") == 5.0

    movs = inv.obtener_movimientos()
    movs[0]["codigo"] = "HACK"
    assert inv.obtener_movimientos()[0]["codigo"] == "P11"

    informe = inv.generar_informe_operativo(bodega="A")
    informe["movimientos_recientes"].clear()
    assert len(inv.generar_informe_operativo(bodega="A")["movimientos_recientes"]) == 1


def test_informe_bodega_solo_10_recientes():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P12", nombre="Lote", costo=1, cantidad=100, bodega="W",
    )
    for i in range(12):
        inv.procesar_operacion_completa("SALIDA", "P12", cantidad=1, bodega="W")
    informe = inv.generar_informe_operativo(bodega="W")
    assert len(informe["movimientos_recientes"]) == 10
    assert informe["movimientos_recientes"][-1]["tipo"] == "SALIDA"


def test_valorizar_y_bajo_minimo():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P13", nombre="Bajo", costo=10, cantidad=2,
        stock_minimo=10, bodega="A",
    )
    val = inv.valorizar()
    assert val["total"] == 20.0
    bajo = inv.productos_bajo_minimo()
    assert len(bajo) == 1
    assert bajo[0]["codigo"] == "P13"


def test_costo_se_conserva_si_stock_total_queda_en_cero_por_formula():
    """
    Si tras una entrada el nuevo_total fuera 0, se conserva el costo anterior.
    Escenario con stock negativo previo (forzar) + entrada que deja total en 0.
    """
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P14", nombre="Neg", costo=40, cantidad=5, bodega="A",
    )
    inv.procesar_operacion_completa(
        "SALIDA", "P14", cantidad=8, bodega="A", forzar=True,
    )
    # stock total = -3, costo 40
    # entrada de 3: nuevo_total = 0 -> conservar costo 40
    r = inv.procesar_operacion_completa(
        "ENTRADA", "P14", costo=99, cantidad=3, bodega="A",
    )
    assert r["ok"] is True
    assert inv.consultar_stock("P14")["stock_total"] == 0
    assert inv.consultar_stock("P14")["costo_promedio"] == 40.0


def test_formula_con_stock_negativo_se_aplica_tal_cual():
    inv = SistemaGestionInventario(reloj=reloj_fijo)
    inv.procesar_operacion_completa(
        "ENTRADA", "P15", nombre="Neg2", costo=10, cantidad=2, bodega="A",
    )
    inv.procesar_operacion_completa(
        "SALIDA", "P15", cantidad=5, bodega="A", forzar=True,
    )
    # stock = -3, costo = 10; entrada 2 a costo 20
    # ((-3)*10 + 2*20) / (-3+2) = (-30+40)/(-1) = -10.0
    r = inv.procesar_operacion_completa(
        "ENTRADA", "P15", costo=20, cantidad=2, bodega="A",
    )
    assert r["ok"] is True
    assert inv.consultar_stock("P15")["costo_promedio"] == -10.0
