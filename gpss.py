import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Comparador GPSS Minería", layout="wide")

st.title("Comparador de Escenarios GPSS")
st.markdown("### Sistema de carguío y acarreo minero")


# =========================================================
# LECTURA DE ARCHIVO
# =========================================================

def leer_archivo(archivo):
    return archivo.read().decode("utf-8", errors="ignore")


# =========================================================
# EXTRACCION DE DATOS GPSS
# =========================================================

def extraer_facility(texto):
    datos = []

    for linea in texto.splitlines():
        p = linea.split()

        if len(p) >= 4 and p[0].startswith("EXC"):
            try:
                datos.append({
                    "Excavadora": p[0],
                    "Entradas": float(p[1]),
                    "Utilización (%)": float(p[2]) * 100,
                    "Tiempo prom. carga (s)": float(p[3])
                })
            except ValueError:
                pass

    return pd.DataFrame(datos)


def extraer_queue(texto):
    datos = []

    for linea in texto.splitlines():
        p = linea.split()

        if len(p) >= 8 and p[0].startswith("COLEX"):
            try:
                datos.append({
                    "Cola": p[0],
                    "Cola máxima": float(p[1]),
                    "Cola final": float(p[2]),
                    "Entradas": float(p[3]),
                    "Entradas sin espera": float(p[4]),
                    "Cola promedio": float(p[5]),
                    "Tiempo prom. cola (s)": float(p[6]),
                    "Tiempo prom. si esperó (s)": float(p[7])
                })
            except ValueError:
                pass

    return pd.DataFrame(datos)


def extraer_storage(texto):
    datos = []

    for linea in texto.splitlines():
        p = linea.split()

        if len(p) >= 9 and p[0] in ["BOT5", "PAD7"]:
            try:
                datos.append({
                    "Zona": p[0],
                    "Capacidad": float(p[1]),
                    "Remanente final": float(p[2]),
                    "Mín. ocupación": float(p[3]),
                    "Máx. ocupación": float(p[4]),
                    "Entradas": float(p[5]),
                    "Disponible": float(p[6]),
                    "Ocupación promedio": float(p[7]),
                    "Utilización (%)": float(p[8]) * 100
                })
            except ValueError:
                pass

    return pd.DataFrame(datos)


def extraer_savevalues(texto):
    datos = {}

    leyendo = False

    for linea in texto.splitlines():
        p = linea.split()

        if len(p) >= 1 and p[0] == "SAVEVALUE":
            leyendo = True
            continue

        if leyendo and len(p) >= 1 and p[0] in ["FEC", "CEC"]:
            break

        if leyendo and len(p) >= 3:
            try:
                datos[p[0]] = float(p[2])
            except ValueError:
                pass

    return datos


# =========================================================
# ANALISIS DEL REPORTE
# =========================================================

def analizar_reporte(texto):
    facility = extraer_facility(texto)
    queue = extraer_queue(texto)
    storage = extraer_storage(texto)
    save = extraer_savevalues(texto)

    padlix1 = save.get("PADLIX1", 0)
    padlix2 = save.get("PADLIX2", 0)
    botadero = save.get("BOTADERO", 0)

    mineral_total = save.get("MINERALTOTAL", padlix1 + padlix2)
    prod_total = save.get("PRODTOTAL", mineral_total + botadero)
    viajes_total = save.get("VIAJESTOTAL", 0)

    horas = 10

    util_prom = facility["Utilización (%)"].mean() if not facility.empty else 0
    util_min = facility["Utilización (%)"].min() if not facility.empty else 0
    util_max = facility["Utilización (%)"].max() if not facility.empty else 0
    desbalance_util = util_max - util_min

    cola_prom = queue["Tiempo prom. cola (s)"].mean() if not queue.empty else 0
    cola_max = queue["Cola máxima"].max() if not queue.empty else 0
    cola_promedio_camiones = queue["Cola promedio"].mean() if not queue.empty else 0

    entradas_colas = queue["Entradas"].sum() if not queue.empty else 0
    entradas_sin_espera = queue["Entradas sin espera"].sum() if not queue.empty else 0
    porcentaje_sin_espera = (entradas_sin_espera / entradas_colas) * 100 if entradas_colas else 0

    ratio_dm = botadero / mineral_total if mineral_total else 0
    ratio_md = mineral_total / botadero if botadero else 0

    kpis = {
        "Mineral total (t)": mineral_total,
        "Desmonte total (t)": botadero,
        "Producción total (t)": prod_total,
        "Mineral por hora (t/h)": mineral_total / horas,
        "Producción total por hora (t/h)": prod_total / horas,
        "Ratio desmonte/mineral": ratio_dm,
        "Ratio mineral/desmonte": ratio_md,
        "Viajes totales": viajes_total,
        "Toneladas por viaje": prod_total / viajes_total if viajes_total else 0,
        "Utilización promedio excavadoras (%)": util_prom,
        "Utilización mínima excavadoras (%)": util_min,
        "Utilización máxima excavadoras (%)": util_max,
        "Desbalance de utilización (%)": desbalance_util,
        "Tiempo promedio de cola (s)": cola_prom,
        "Cola máxima global": cola_max,
        "Cola promedio global (camiones)": cola_promedio_camiones,
        "% entradas sin espera": porcentaje_sin_espera,
        "PADLIX1 (t)": padlix1,
        "PADLIX2 (t)": padlix2,
        "BOTADERO (t)": botadero,
        "CARGAS1": save.get("CARGAS1", 0),
        "CARGAS2": save.get("CARGAS2", 0),
        "CARGAS3": save.get("CARGAS3", 0),
        "DESCARGAS1": save.get("DESCARGAS1", 0),
        "DESCARGAS2": save.get("DESCARGAS2", 0),
        "DESCARGAS3": save.get("DESCARGAS3", 0),
    }

    return {
        "facility": facility,
        "queue": queue,
        "storage": storage,
        "save": save,
        "kpis": kpis
    }


# =========================================================
# GRAFICOS PLOTLY
# =========================================================

def grafico_comparativo(df, categoria, titulo, ylabel):
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df[categoria],
        y=df["Escenario 1"],
        name="Escenario 1",
        text=df["Escenario 1"].round(2),
        textposition="outside"
    ))

    fig.add_trace(go.Bar(
        x=df[categoria],
        y=df["Escenario 2"],
        name="Escenario 2",
        text=df["Escenario 2"].round(2),
        textposition="outside"
    ))

    fig.update_layout(
        title=titulo,
        xaxis_title=categoria,
        yaxis_title=ylabel,
        barmode="group",
        height=470,
        template="plotly_dark",
        legend_title="Escenario"
    )

    st.plotly_chart(fig, use_container_width=True)


def comparar_tablas(df1, df2, clave, columna):
    if df1.empty or df2.empty:
        return pd.DataFrame()

    df = pd.merge(
        df1[[clave, columna]],
        df2[[clave, columna]],
        on=clave,
        how="outer",
        suffixes=(" Escenario 1", " Escenario 2")
    ).fillna(0)

    df = df.rename(columns={
        f"{columna} Escenario 1": "Escenario 1",
        f"{columna} Escenario 2": "Escenario 2"
    })

    df["Diferencia"] = df["Escenario 2"] - df["Escenario 1"]
    return df


# =========================================================
# PUNTAJE Y RECOMENDACION
# =========================================================

def puntaje_escenario(kpis):
    mineral = kpis["Mineral total (t)"]
    util = kpis["Utilización promedio excavadoras (%)"]
    cola = kpis["Tiempo promedio de cola (s)"]
    desbalance = kpis["Desbalance de utilización (%)"]
    ratio_dm = kpis["Ratio desmonte/mineral"]
    sin_espera = kpis["% entradas sin espera"]

    # Escala ponderada:
    # + mineral: mayor producción útil
    # + utilización: mejor uso de excavadoras
    # + entradas sin espera: menor congestión
    # - cola: penaliza espera
    # - desbalance: penaliza que una excavadora trabaje demasiado y otra poco
    # - ratio desmonte/mineral excesivo: penaliza demasiado desmonte frente al mineral

    return (
        mineral
        + util * 80
        + sin_espera * 20
        - cola * 35
        - desbalance * 60
        - ratio_dm * 1000
    )


def explicar_eleccion(k1, k2, p1, p2):
    if p2 > p1:
        ganador = "Escenario 2"
        kg = k2
        kp = k1
    elif p1 > p2:
        ganador = "Escenario 1"
        kg = k1
        kp = k2
    else:
        return "Ambos escenarios tienen desempeño muy similar según el criterio multicriterio."

    razones = []

    if kg["Mineral total (t)"] > kp["Mineral total (t)"]:
        razones.append("produce más mineral útil")
    if kg["Tiempo promedio de cola (s)"] < kp["Tiempo promedio de cola (s)"]:
        razones.append("tiene menor tiempo promedio de cola")
    if kg["Desbalance de utilización (%)"] < kp["Desbalance de utilización (%)"]:
        razones.append("presenta mejor balance entre excavadoras")
    if kg["% entradas sin espera"] > kp["% entradas sin espera"]:
        razones.append("tiene mayor porcentaje de camiones que ingresan sin esperar")
    if kg["Ratio desmonte/mineral"] < kp["Ratio desmonte/mineral"]:
        razones.append("mueve menos desmonte por tonelada de mineral")
    if kg["Utilización promedio excavadoras (%)"] > kp["Utilización promedio excavadoras (%)"]:
        razones.append("usa mejor las excavadoras en promedio")

    if not razones:
        razones.append("presenta mejor puntaje combinado entre producción, colas y balance operativo")

    return f"El {ganador} es recomendable porque " + ", ".join(razones) + "."


# =========================================================
# INTERFAZ
# =========================================================

col_arch1, col_arch2 = st.columns(2)

with col_arch1:
    archivo1 = st.file_uploader("📄 Reporte GPSS - Escenario 1", type=["txt"], key="esc1")

with col_arch2:
    archivo2 = st.file_uploader("📄 Reporte GPSS - Escenario 2", type=["txt"], key="esc2")


if archivo1 and archivo2:
    texto1 = leer_archivo(archivo1)
    texto2 = leer_archivo(archivo2)

    r1 = analizar_reporte(texto1)
    r2 = analizar_reporte(texto2)

    k1 = r1["kpis"]
    k2 = r2["kpis"]

    st.markdown("---")
    st.header("📌 Resumen principal")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Mineral total",
        f"{k2['Mineral total (t)']:.2f} t",
        f"{k2['Mineral total (t)'] - k1['Mineral total (t)']:.2f} t"
    )

    c2.metric(
        "Cola promedio",
        f"{k2['Tiempo promedio de cola (s)']:.2f} s",
        f"{k2['Tiempo promedio de cola (s)'] - k1['Tiempo promedio de cola (s)']:.2f} s"
    )

    c3.metric(
        "Utilización prom.",
        f"{k2['Utilización promedio excavadoras (%)']:.2f} %",
        f"{k2['Utilización promedio excavadoras (%)'] - k1['Utilización promedio excavadoras (%)']:.2f} %"
    )

    c4.metric(
        "Desbalance util.",
        f"{k2['Desbalance de utilización (%)']:.2f} %",
        f"{k2['Desbalance de utilización (%)'] - k1['Desbalance de utilización (%)']:.2f} %"
    )

    st.markdown("---")
    st.header("📋 Comparación completa de KPIs")

    indicadores = list(k1.keys())

    df_kpis = pd.DataFrame({
        "Indicador": indicadores,
        "Escenario 1": [k1.get(i, 0) for i in indicadores],
        "Escenario 2": [k2.get(i, 0) for i in indicadores],
    })

    df_kpis["Diferencia"] = df_kpis["Escenario 2"] - df_kpis["Escenario 1"]
    st.dataframe(df_kpis, use_container_width=True)

    st.markdown("---")
    st.header("📦 Producción comparativa")

    df_prod = pd.DataFrame({
        "Indicador": ["Mineral total", "Desmonte total", "Producción total"],
        "Escenario 1": [
            k1["Mineral total (t)"],
            k1["Desmonte total (t)"],
            k1["Producción total (t)"]
        ],
        "Escenario 2": [
            k2["Mineral total (t)"],
            k2["Desmonte total (t)"],
            k2["Producción total (t)"]
        ]
    })

    grafico_comparativo(df_prod, "Indicador", "Producción y tonelaje", "Toneladas")

    st.markdown("---")
    st.header("⛏️ Utilización de excavadoras")

    df_util = comparar_tablas(
        r1["facility"],
        r2["facility"],
        "Excavadora",
        "Utilización (%)"
    )

    if not df_util.empty:
        grafico_comparativo(df_util, "Excavadora", "Utilización por excavadora", "Utilización (%)")
        st.dataframe(df_util, use_container_width=True)
    else:
        st.warning("No se pudieron leer datos FACILITY.")

    st.markdown("---")
    st.header("⏱️ Tiempo promedio de cola")

    df_cola = comparar_tablas(
        r1["queue"],
        r2["queue"],
        "Cola",
        "Tiempo prom. cola (s)"
    )

    if not df_cola.empty:
        grafico_comparativo(df_cola, "Cola", "Tiempos de cola", "Segundos")
        st.dataframe(df_cola, use_container_width=True)
    else:
        st.warning("No se pudieron leer datos QUEUE.")

    st.markdown("---")
    st.header("🏗️ Utilización PAD y Botadero")

    df_storage = comparar_tablas(
        r1["storage"],
        r2["storage"],
        "Zona",
        "Utilización (%)"
    )

    if not df_storage.empty:
        grafico_comparativo(df_storage, "Zona", "Uso de PAD y Botadero", "Utilización (%)")
        st.dataframe(df_storage, use_container_width=True)
    else:
        st.warning("No se pudieron leer datos STORAGE.")

    st.markdown("---")
    st.header("🚛 Cargas y descargas")

    df_cargas = pd.DataFrame({
        "Indicador": [
            "CARGAS1", "CARGAS2", "CARGAS3",
            "DESCARGAS1", "DESCARGAS2", "DESCARGAS3"
        ],
        "Escenario 1": [
            k1["CARGAS1"], k1["CARGAS2"], k1["CARGAS3"],
            k1["DESCARGAS1"], k1["DESCARGAS2"], k1["DESCARGAS3"]
        ],
        "Escenario 2": [
            k2["CARGAS1"], k2["CARGAS2"], k2["CARGAS3"],
            k2["DESCARGAS1"], k2["DESCARGAS2"], k2["DESCARGAS3"]
        ]
    })

    grafico_comparativo(df_cargas, "Indicador", "Cargas y descargas", "Cantidad")
    st.dataframe(df_cargas, use_container_width=True)

    st.markdown("---")
    st.header("✅ Recomendación automática multicriterio")

    p1 = puntaje_escenario(k1)
    p2 = puntaje_escenario(k2)

    colp1, colp2 = st.columns(2)
    colp1.metric("Puntaje Escenario 1", f"{p1:.2f}")
    colp2.metric("Puntaje Escenario 2", f"{p2:.2f}")

    st.info(
        "El puntaje considera producción mineral, utilización promedio, porcentaje sin espera, "
        "tiempo de cola, balance entre excavadoras y ratio desmonte/mineral."
    )

    explicacion = explicar_eleccion(k1, k2, p1, p2)

    if p2 > p1:
        st.success(explicacion)
    elif p1 > p2:
        st.success(explicacion)
    else:
        st.warning(explicacion)

else:
    st.info("⬆️ Sube dos reportes `.txt` generados desde GPSS para iniciar la comparación.")