import json
import time

from app.gestor_fuentes import gestionar_fuentes


def fuente_correcta(url):
    return {"mensaje": "Consulta exitosa", "error": None}


def fuente_con_error(url):
    raise ConnectionError("Fallo simulado")


def fuente_lenta(url):
    time.sleep(15)
    return {"mensaje": "Respuesta tardía", "error": None}


if __name__ == "__main__":
    fuentes = {
        "correcta": (
            "prueba_hu10", "fuente_correcta", "https://example.com"
        ),
        "con_error": (
            "prueba_hu10", "fuente_con_error", "https://example.com"
        ),
        "lenta": (
            "prueba_hu10", "fuente_lenta", "https://example.com"
        ),
    }

    resultado = gestionar_fuentes(fuentes)

    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    assert resultado["estado"] == "parcial"
    assert resultado["fuentes"]["correcta"]["estado"] == "ok"
    assert resultado["fuentes"]["con_error"]["estado"] == "error"
    assert resultado["fuentes"]["lenta"]["estado"] == "timeout"

    print("Prueba correcta: se conservó el resultado disponible.")
    print("La fuente con error y la fuente lenta fueron omitidas.")