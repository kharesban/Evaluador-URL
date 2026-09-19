from app.validador.analisisUrl   import *

def menu():
    
    print("""Prueba de analisis de Urls
          Para iniciar ingresa url o si quieres salir escribir 'salir' para finalizar""")
    
    while True:
        url_entrada = input("Ingrese el url para analizar: ")
        
        if(url_entrada.strip() == "salir"):
            print("Hasta pronto, vuelve cuando quieras analizar una URL...")
            break 
        elif not url_entrada.strip():
            print("Parece que no has ingresaddo ninguna URL... ")
            continue
        else:
            es_valido, url_normalizada, error = normalizacion_analisis_url(url_entrada)
            
            if es_valido:
                print("✅ ESTADO: URL VÁLIDA Y NORMALIZADA")
                print(f"✅Entrada original:   {url_entrada}")
                print(f"🔄 URL Normalizada:    {url_normalizada}")
                
            else:
                print("❌ ESTADO: URL INVÁLIDA")
                print(f"❌ Entrada original:   {url_entrada}")
                print(f"⚠️ Causa del rechazo:  {error}")
                print("-" * 40 + "\n")

if __name__ == "__main__":
    menu()