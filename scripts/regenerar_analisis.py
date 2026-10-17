# -*- coding: utf-8 -*-
"""
Regenera reportes de análisis estático y dinámico (antes / después).
Uso: python scripts/regenerar_analisis.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANTES_SRC = ROOT / "evidencia" / "antes" / "gestion_inventario.py"
DESPUES_SRC = ROOT / "gestion_inventario.py"
DIR_ANTES = ROOT / "analisis" / "antes"
DIR_DESPUES = ROOT / "analisis" / "despues"
CARGA = ROOT / "carga" / "carga_fija.py"


def run(cmd, cwd=None, outfile=None, shell=False):
    printable = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(">", printable)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=shell,
        )
    except FileNotFoundError as exc:
        text = f"[error] comando no encontrado: {printable}\n{exc}\n"
        if outfile:
            outfile.write_text(text, encoding="utf-8")
        return 127, text
    text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if outfile:
        outfile.write_text(text, encoding="utf-8")
    return result.returncode, text


def detectar_duplicacion_simple(fuente: Path, destino: Path):
    """Respaldo local si jscpd/npx no está disponible: bloques repetidos de 5+ líneas."""
    lineas = fuente.read_text(encoding="utf-8").splitlines()
    ventana = 5
    vistos = {}
    clones = []
    for i in range(len(lineas) - ventana + 1):
        bloque = tuple(l.strip() for l in lineas[i : i + ventana] if l.strip())
        if len(bloque) < ventana:
            continue
        if bloque in vistos:
            clones.append(
                {
                    "primera": vistos[bloque] + 1,
                    "segunda": i + 1,
                    "lineas": ventana,
                    "muestra": " | ".join(bloque[:2]),
                }
            )
        else:
            vistos[bloque] = i
    # deduplicar por par de líneas
    unicos = []
    vistos_pares = set()
    for c in clones:
        clave = (c["primera"], c["segunda"])
        if clave not in vistos_pares:
            vistos_pares.add(clave)
            unicos.append(c)
    reporte = {
        "herramienta": "detector_local_bloques",
        "archivo": str(fuente),
        "clones_encontrados": len(unicos),
        "detalle": unicos[:50],
    }
    (destino / "jscpd_local.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (destino / "jscpd_console.txt").write_text(
        f"Clones de bloques ({ventana} lineas): {len(unicos)}\n"
        + "\n".join(
            f"L{c['primera']} ~ L{c['segunda']}: {c['muestra']}" for c in unicos[:30]
        ),
        encoding="utf-8",
    )
    return len(unicos)


def analizar(fuente: Path, destino: Path, etiqueta: str):
    destino.mkdir(parents=True, exist_ok=True)
    # Copia temporal como gestion_inventario.py para imports de carga/tests
    trabajo = ROOT / "_tmp_analisis"
    if trabajo.exists():
        shutil.rmtree(trabajo)
    trabajo.mkdir()
    shutil.copy2(fuente, trabajo / "gestion_inventario.py")

    # --- Estáticos ---
    run(
        [sys.executable, "-m", "pylint", str(trabajo / "gestion_inventario.py"), "-f", "text"],
        outfile=destino / "pylint.txt",
    )
    run(
        [sys.executable, "-m", "radon", "cc", str(trabajo / "gestion_inventario.py"), "-s", "-a"],
        outfile=destino / "radon_cc.txt",
    )
    run(
        [sys.executable, "-m", "radon", "mi", str(trabajo / "gestion_inventario.py"), "-s"],
        outfile=destino / "radon_mi.txt",
    )
    run(
        [sys.executable, "-m", "radon", "raw", str(trabajo / "gestion_inventario.py")],
        outfile=destino / "radon_raw.txt",
    )
    run(
        [sys.executable, "-m", "vulture", str(trabajo / "gestion_inventario.py")],
        outfile=destino / "vulture.txt",
    )

    # jscpd (npx en Windows) + respaldo local
    jscpd_out = destino / "jscpd"
    jscpd_out.mkdir(exist_ok=True)
    code, text = run(
        f'npx --yes jscpd "{trabajo / "gestion_inventario.py"}" '
        f'--reporters json,console --output "{jscpd_out}" --min-lines 5',
        shell=True,
    )
    if code != 0 or "error" in text.lower()[:200]:
        n = detectar_duplicacion_simple(trabajo / "gestion_inventario.py", destino)
        extra = (
            f"\n[aviso] jscpd/npx no disponible (code={code}). "
            f"Se usó detector local: {n} clones de bloques.\n{text}\n"
        )
        prev = (destino / "jscpd_console.txt").read_text(encoding="utf-8")
        (destino / "jscpd_console.txt").write_text(prev + extra, encoding="utf-8")
    else:
        (destino / "jscpd_console.txt").write_text(text, encoding="utf-8")

    # --- Dinámicos: activar módulo bajo análisis ---
    actual = ROOT / "gestion_inventario.py"
    respaldo = ROOT / "gestion_inventario.py.bak_analisis"
    mismo_archivo = fuente.resolve() == actual.resolve()
    if not mismo_archivo:
        shutil.copy2(actual, respaldo)
    try:
        if not mismo_archivo:
            shutil.copy2(fuente, actual)

        # pytest + coverage
        run(
            [
                sys.executable, "-m", "coverage", "run",
                "--source=gestion_inventario",
                "-m", "pytest", "tests/test_comportamiento_fijo.py", "-q",
            ],
        )
        run(
            [sys.executable, "-m", "coverage", "report", "-m"],
            outfile=destino / "coverage.txt",
        )
        run(
            [sys.executable, "-m", "coverage", "json", "-o", str(destino / "coverage.json")],
        )

        # cProfile sobre carga fija
        run(
            [
                sys.executable, "-m", "cProfile", "-s", "cumtime",
                str(CARGA),
            ],
            outfile=destino / "cprofile.txt",
        )

        # trace
        run(
            [
                sys.executable, "-m", "trace", "--count", "--summary",
                str(CARGA),
            ],
            outfile=destino / "trace.txt",
        )

        # checksum carga
        code, digest_out = run([sys.executable, str(CARGA)])
        digest = digest_out.strip().splitlines()[-1] if digest_out.strip() else ""
        (destino / "checksum_carga.txt").write_text(digest + "\n", encoding="utf-8")

        meta = {
            "etiqueta": etiqueta,
            "fuente": str(fuente),
            "checksum_carga": digest,
        }
        (destino / "meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    finally:
        if not mismo_archivo and respaldo.exists():
            shutil.copy2(respaldo, actual)
            respaldo.unlink(missing_ok=True)
        shutil.rmtree(trabajo, ignore_errors=True)

    print(f"[{etiqueta}] listo en {destino}")


def main():
    DIR_ANTES.mkdir(parents=True, exist_ok=True)
    DIR_DESPUES.mkdir(parents=True, exist_ok=True)
    analizar(ANTES_SRC, DIR_ANTES, "antes")
    analizar(DESPUES_SRC, DIR_DESPUES, "despues")

    a = (DIR_ANTES / "checksum_carga.txt").read_text(encoding="utf-8").strip()
    b = (DIR_DESPUES / "checksum_carga.txt").read_text(encoding="utf-8").strip()
    cmp_path = ROOT / "analisis" / "comparacion_checksum.txt"
    cmp_path.write_text(
        f"antes={a}\ndespues={b}\nidenticos={a == b}\n",
        encoding="utf-8",
    )
    print("Checksums idénticos:", a == b)
    if a != b:
        sys.exit(1)


if __name__ == "__main__":
    main()
