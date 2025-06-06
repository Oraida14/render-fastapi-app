from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os, traceback

app = FastAPI()

# --------- CORS (para JS del navegador) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Rutas y carpetas ---------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "statics")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
DATOS_DIR = os.path.join(TEMPLATE_DIR, "datos_individuales")

# --------- Montar carpetas ---------
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "statics")), name="static")

app.mount("/datos_individuales", StaticFiles(directory=DATOS_DIR), name="datos")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --------- Página principal ---------
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --------- Endpoint: Datos resumidos tanque ---------
@app.get("/datos-resumidos/tanque3cantos")
def obtener_datos_tanque3cantos():
    try:
        tanque_file = os.path.join(DATOS_DIR, "tanque3cantos.csv")
        df = pd.read_csv(tanque_file)
        if df.empty or "fecha_hora" not in df.columns:
            raise ValueError("CSV vacío o mal formateado")

        df["timestamp"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)
        ultimo = df.iloc[0]

        # Entrada total
        entrada = 0.0
        for pozo in ["p263.csv", "p25.csv"]:
            f = os.path.join(DATOS_DIR, pozo)
            if os.path.isfile(f):
                d = pd.read_csv(f)
                if {"fecha_hora", "Gasto_Instantaneo"}.issubset(d.columns):
                    d = d.dropna(subset=["fecha_hora"]).sort_values("fecha_hora", ascending=False)
                    entrada += float(d.iloc[0]["Gasto_Instantaneo"])

        # Salida total
        salida = 0.0
        for reb in ["reb62.csv", "reb62a.csv"]:
            f = os.path.join(DATOS_DIR, reb)
            if os.path.isfile(f):
                d = pd.read_csv(f)
                if {"fecha_hora", "Gasto_Instantaneo"}.issubset(d.columns):
                    d = d.dropna(subset=["fecha_hora"]).sort_values("fecha_hora", ascending=False)
                    salida += float(d.iloc[0]["Gasto_Instantaneo"])

        return {
            "timestamp": str(ultimo["timestamp"]),
            "nivel": round(float(ultimo.get("Nivel_1", 0.0)), 2),
            "volumen_estimado": round(float(ultimo.get("volumen_m3", 0.0)), 2),
            "entrada": round(entrada, 2),
            "salida": round(salida, 2)
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --------- Historial de nivel del tanque (últimas 24 h) ---------
@app.get("/historial/tanque3cantos")
def historial_nivel():
    try:
        f = os.path.join(DATOS_DIR, "tanque3cantos.csv")
        if not os.path.isfile(f):
            raise HTTPException(404, "CSV de tanque no encontrado")

        d = pd.read_csv(f, parse_dates=["fecha_hora"])
        if "Nivel_1" not in d.columns:
            raise HTTPException(400, "Columna Nivel_1 no encontrada")

        limite = d["fecha_hora"].max() - pd.Timedelta(hours=24)
        d = d[d["fecha_hora"] >= limite].sort_values("fecha_hora")

        d["fecha_hora"] = d["fecha_hora"].astype(str)
        d["Nivel_1"] = d["Nivel_1"].round(2)
        return {"historial": d[["fecha_hora", "Nivel_1"]].to_dict(orient="records")}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))

# --------- Historial de salida de rebombeo (24 h) ---------
@app.get("/historial/salida-rebombeo")
def historial_salida():
    try:
        frames = []
        for csv in ["reb62.csv", "reb62a.csv"]:
            f = os.path.join(DATOS_DIR, csv)
            if os.path.isfile(f):
                d = pd.read_csv(f, parse_dates=["fecha_hora"])
                d = d[["fecha_hora", "Gasto_Instantaneo"]].dropna()
                frames.append(d)

        if not frames:
            raise HTTPException(404, "Sin datos de rebombeo")

        df = pd.concat(frames)
        df = df.groupby("fecha_hora", as_index=False)["Gasto_Instantaneo"].sum()
        limite = df["fecha_hora"].max() - pd.Timedelta(hours=24)
        df = df[df["fecha_hora"] >= limite].sort_values("fecha_hora")

        df["fecha_hora"] = df["fecha_hora"].astype(str)
        df["Gasto_Instantaneo"] = df["Gasto_Instantaneo"].round(2)
        return {"historial": df.rename(columns={"Gasto_Instantaneo": "salida_total"}).to_dict(orient="records")}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))

# --------- Resumen genérico para cualquier archivo CSV ---------
@app.get("/datos-resumidos/{nombre}")
def resumen_generico(nombre: str):
    try:
        f = os.path.join(DATOS_DIR, f"{nombre}.csv")
        if not os.path.isfile(f):
            raise HTTPException(404, "Archivo no existe")

        d = pd.read_csv(f, parse_dates=["fecha_hora"])
        ult = d["fecha_hora"].max()
        return {"sitio": nombre, "ult_dato": str(ult)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


#uvicorn api:app --reload --port 8000
#uvicorn api:app --reload --port 8001 solo local
# uvicorn api:app --reload --host 0.0.0.0 --port 8001 otras maquinas 
