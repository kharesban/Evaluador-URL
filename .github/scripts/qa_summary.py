"""Publicar métricas reales y comprobar el umbral por módulo evaluado."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    carpeta = Path("qa-results")
    cobertura = json.loads((carpeta / "coverage.json").read_text())
    raiz = ET.parse(carpeta / "junit.xml").getroot()
    suites = list(raiz.iter("testsuite"))
    total = sum(int(s.get("tests", 0)) for s in suites)
    fallidos = sum(int(s.get("failures", 0)) for s in suites)
    errores = sum(int(s.get("errors", 0)) for s in suites)
    omitidos = sum(int(s.get("skipped", 0)) for s in suites)
    aprobados = total - fallidos - errores - omitidos
    duracion = sum(float(s.get("time", 0)) for s in suites)
    t = cobertura["totals"]
    lineas = [
        "## Resultados QA", "",
        f"Commit: `{os.getenv('GITHUB_SHA', 'ejecucion-local')}`", "",
        f"Casos ejecutados: **{total}**; aprobados: **{aprobados}**; fallos: **{fallidos}**; errores: **{errores}**; omitidos: **{omitidos}**.",
        f"Duración de la suite (JUnit): **{duracion:.3f} s**.",
        f"Tasa de aprobación: **{100 * aprobados / total if total else 0:.2f}%** (no equivale a cobertura de código).",
        f"Cobertura agregada de líneas y ramas: **{t['percent_covered']:.2f}%**.", "",
        "| Módulo | Líneas cubiertas / totales | Ramas cubiertas / totales | Cobertura combinada |",
        "|---|---:|---:|---:|",
    ]
    bajos = []
    for archivo, datos in cobertura["files"].items():
        s = datos["summary"]
        if s['num_statements'] == 0:
            lineas.append(f"| {archivo} | Sin código ejecutable | - | No aplica |")
            continue
        lineas.append(f"| {archivo} | {s['covered_lines']}/{s['num_statements']} | {s.get('covered_branches', 0)}/{s.get('num_branches', 0)} | {s['percent_covered']:.2f}% |")
        cobertura_lineas = 100 * s['covered_lines'] / s['num_statements']
        cobertura_ramas = 100 * s.get('covered_branches', 0) / s['num_branches'] if s.get('num_branches', 0) else 100
        if min(s["percent_covered"], cobertura_lineas, cobertura_ramas) < 70:
            bajos.append(archivo)
    lineas += ["", "Alcance: API FastAPI, gestor, worker, configuración, validadores, clasificación y adaptadores de fuentes del backend web. Se excluyen los dos scripts manuales antiguos y el bloque CLI del worker. Las conexiones externas están simuladas. Los archivos vacíos no acreditan funcionalidades implementadas."]
    resumen = "\n".join(lineas) + "\n"
    (carpeta / "resumen.md").write_text(resumen, encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as salida:
            salida.write(resumen)
    print(resumen)
    if bajos:
        raise SystemExit("Cobertura inferior al 70% en: " + ", ".join(bajos))


if __name__ == "__main__":
    main()
