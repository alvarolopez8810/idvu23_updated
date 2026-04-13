import json
import os
from datetime import date

import boto3
import pandas as pd
from dotenv import load_dotenv

ejecucion = "local"
# 1. Define the base path
ruta_base = "../scraping/data/south_america/"
#ruta_base = "../scraping/data/n_c_america/"
if (ejecucion == "s3"):
    # Cargar variables de entorno
    load_dotenv()
    BUCKET_NAME = os.getenv("AWS_BUCKET")
    START_PREFIX = "data"
    s3 = boto3.client("s3")

paises = [
    #"panama",
    #"colombia",
    "argentina",
    #"brazil",
    #"uruguay",
    #"paraguay",
    #"ecuador",
    #"venezuela",
]

print("INICIANDO SCRIPT")

def list_all_s3_keys(bucket, prefix):
    """Lista todas las claves en un bucket S3 con el prefijo dado."""
    keys = []
    continuation_token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = s3.list_objects_v2(**kwargs)
        for obj in response.get("Contents", []):
            keys.append(obj["Key"])
        if response.get("IsTruncated"):
            continuation_token = response["NextContinuationToken"]
        else:
            break
    return keys

def s3_read_json(bucket, key):
    """Lee un archivo JSON desde S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))

def get_all_paths(pais):
    if ejecucion == "s3":
        return list_all_s3_keys(BUCKET_NAME, START_PREFIX)
    else:
        # 1. Define the base path
        ruta = ruta_base + pais
        # 2. List all competitions (subdirectories) recursively
        squads_files = []
        for root, dirs, files in os.walk(ruta):
            if "squads.json" in files:
                squads_files.append(os.path.join(root, "squads.json"))
        return squads_files

def readJsonSquad(jsonSquadFile):
    if ejecucion == "s3":
        return s3_read_json(BUCKET_NAME, jsonSquadFile)
    else:
        with open(jsonSquadFile, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

for pais in paises:
    competiciones = []
    print("OBTAINING THE PATHS")
    # Obtener todas las claves del bucket
    all_keys = get_all_paths(pais)
    print("PATHS: ", all_keys)

    for ruta in all_keys:
        if (
            ("2026" in ruta)
            and ruta.endswith("squads.json")
            and pais.replace(" ", "_").lower() in ruta
        ):
            competiciones.append(ruta)

    # Inicializar un DataFrame vacio para el resultado final
    jugadores_filtrados = pd.DataFrame(
        columns=["competicion", "equipo", "jugador", "posicion", "fecha_nacimiento", "id"]
    )

    # Definir los rangos de fecha
    fecha_inicio = date(2003, 1, 1)
    fecha_fin = date(2009, 12, 31)

    # Si se encontraron archivos, procesarlos
    if len(competiciones) > 0:
        for ruta_json in competiciones:
            print(f"Procesando archivo: {ruta_json}")
            data = readJsonSquad(ruta_json)

            # Navegamos por el objeto 'squad' dentro del JSON
            if data.get("squad") is not None:
                ruta_femenino = False

                for equipo_item in data["squad"]:
                    if ruta_femenino:
                        continue

                    if equipo_item.get("type") == "women":
                        print(f"Futbol femenino en: {ruta_json}")
                        ruta_femenino = True
                        continue

                    competicion = equipo_item.get("competitionName", "")
                    nombre_equipo = equipo_item.get("contestantName", "")

                    # Comprobar si existe la lista 'person'
                    if equipo_item.get("person") is not None:
                        for jugador in equipo_item["person"]:
                            dob = jugador.get("dateOfBirth")
                            if dob is not None and dob != "":
                                try:
                                    fecha_nacimiento = date.fromisoformat(dob)
                                except ValueError:
                                    continue

                                if fecha_inicio <= fecha_nacimiento <= fecha_fin:
                                    nueva_fila = {
                                        "competicion": competicion,
                                        "equipo": nombre_equipo,
                                        "jugador": f"{jugador.get('firstName', '')} {jugador.get('lastName', '')}",
                                        "posicion": str(jugador.get("position", "")),
                                        "fecha_nacimiento": str(dob),
                                        "id": str(jugador.get("id", "")),
                                    }

                                    # Verificar si la combinacion ya existe
                                    if not jugadores_filtrados.empty:
                                        existe = (
                                            (jugadores_filtrados["competicion"] == nueva_fila["competicion"])
                                            & (jugadores_filtrados["equipo"] == nueva_fila["equipo"])
                                            & (jugadores_filtrados["id"] == nueva_fila["id"])
                                        ).any()
                                    else:
                                        existe = False

                                    if not existe:
                                        jugadores_filtrados = pd.concat(
                                            [jugadores_filtrados, pd.DataFrame([nueva_fila])],
                                            ignore_index=True,
                                        )
                                    else:
                                        print("La combinacion ya existe, no se anade")

            elif data.get("httpStatus") is not None:
                print(f"Error 404 procesando archivo: {ruta_json}")

    # Guardar el dataframe filtrado en un archivo CSV
    os.makedirs("./listaSub23-2026", exist_ok=True)
    jugadores_filtrados.to_csv(f"./listaSub23-2026/2003-2009 {pais}_actualizado.csv", index=False)
