import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import time
import os

def extract_and_update_data():
    try:
        print("Conectando a la base de datos...")
        db_connection_str = 'mysql+pymysql://admin:Password0@192.168.103.2/datos'
        db_connection = create_engine(db_connection_str)
        print("Conexión a la base de datos exitosa.")

        pozos = ['tanque3cantos', 'p263', 'p25', 'reb62']
        fecha_inicio = (datetime.now() - timedelta(days=60)).replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_limite = fecha_inicio.strftime('%Y-%m-%d %H:%M:%S')

        if not os.path.exists('./templates/datos_individuales'):
            os.makedirs('./templates/datos_individuales')

        resumen_general = []

        for pozo in pozos:
            if pozo == 'p25' or pozo == 'p254':
                query = f"""
                SELECT Gasto_Instantaneo, Presion_Instantanea_3 AS Presion_Instantanea, Nivel_1, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """
            elif pozo == 'reb50':
                query = f"""
                SELECT Gasto_Instantaneo1 AS Gasto_Instantaneo, Presion_Instantanea, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """
            elif pozo == 'p263' or pozo == 'p85':
                query = f"""
                SELECT `Gasto Instantaneo` AS Gasto_Instantaneo, `Presion Instantanea` AS Presion_Instantanea, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """
            elif pozo == 'tanquelajas':
                query = f"""
                SELECT Nivel_1, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """
            elif pozo == 'tanque3cantos':
                query = f"""
                SELECT Nivel_1, Gasto_Instantaneo_3 AS Gasto_Instantaneo, Presion_Instantanea_2 AS Presion_Instantanea, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """
            elif pozo == 'reb62':
                # Procesar reb62 y reb62a por separado
                for sub_pozo, columna in [('reb62', 'Gasto_Reb62'), ('reb62a', 'Gasto_Reb62a')]:
                    query_reb62 = f"""
                    SELECT {columna} AS Gasto_Instantaneo, Presion_Instantanea, t_stamp
                    FROM datos.reb62
                    WHERE t_stamp >= '{fecha_limite}'
                    ORDER BY t_stamp DESC;
                    """
                    df = pd.read_sql(query_reb62, con=db_connection)
                    df['nombre_sitio'] = sub_pozo
                    df['t_stamp'] = pd.to_datetime(df['t_stamp'])
                    df['fecha_hora'] = df['t_stamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

                    resumen = {'Pozo': sub_pozo}
                    columnas_numericas = df.select_dtypes(include='number').columns
                    for col in columnas_numericas:
                        resumen[f'{col}_Promedio'] = round(df[col].mean(), 2)
                        resumen[f'{col}_Mínimo'] = round(df[col].min(), 2)
                        resumen[f'{col}_Máximo'] = round(df[col].max(), 2)
                        resumen[f'{col}_Desviación estándar'] = round(df[col].std(), 2)
                        if len(df[col]) >= 2:
                            inicio = df[col].iloc[-1]
                            fin = df[col].iloc[0]
                            if fin > inicio * 1.05:
                                resumen[f'{col}_Tendencia'] = 'Ascendente'
                            elif fin < inicio * 0.95:
                                resumen[f'{col}_Tendencia'] = 'Descendente'
                            else:
                                resumen[f'{col}_Tendencia'] = 'Estable'
                    resumen_general.append(resumen)
                    df.to_csv(f'datos_individuales/{sub_pozo}.csv', index=False)
                continue  # Saltar al siguiente pozo

            else:
                query = f"""
                SELECT Gasto_Instantaneo, Presion_Instantanea, t_stamp
                FROM datos.{pozo}
                WHERE t_stamp >= '{fecha_limite}'
                ORDER BY t_stamp DESC;
                """

            df = pd.read_sql(query, con=db_connection)
            if df.empty:
                print(f"No hay datos recientes para {pozo}.")
                continue

            df['nombre_sitio'] = pozo
            df['t_stamp'] = pd.to_datetime(df['t_stamp'])
            df['fecha_hora'] = df['t_stamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna('')

            resumen = {'Pozo': pozo}
            columnas_numericas = df.select_dtypes(include='number').columns
            for col in columnas_numericas:
                resumen[f'{col}_Promedio'] = round(df[col].mean(), 2)
                resumen[f'{col}_Mínimo'] = round(df[col].min(), 2)
                resumen[f'{col}_Máximo'] = round(df[col].max(), 2)
                resumen[f'{col}_Desviación estándar'] = round(df[col].std(), 2)
                if len(df[col]) >= 2:
                    inicio = df[col].iloc[-1]
                    fin = df[col].iloc[0]
                    if fin > inicio * 1.05:
                        resumen[f'{col}_Tendencia'] = 'Ascendente'
                    elif fin < inicio * 0.95:
                        resumen[f'{col}_Tendencia'] = 'Descendente'
                    else:
                        resumen[f'{col}_Tendencia'] = 'Estable'

            if 'Gasto_Instantaneo' in df.columns:
                df['volumen_m3'] = df['Gasto_Instantaneo'] * 1/60
                resumen['Volumen_Total_m3'] = round(df['volumen_m3'].sum(), 2)

            if 'Presion_Instantanea' in df.columns:
                anomalias = df[(df['Presion_Instantanea'] < 0) | (df['Presion_Instantanea'] > 100)]
                resumen['Presión_Anómala_Cant'] = len(anomalias)

            df['fecha'] = df['t_stamp'].dt.date
            df['hora'] = df['t_stamp'].dt.hour

            promedios_diarios = df.groupby('fecha').mean(numeric_only=True).reset_index()
            promedios_horarios = df.groupby('hora').mean(numeric_only=True).reset_index()

            df.to_csv(f'datos_individuales/{pozo}.csv', index=False)
            promedios_diarios.to_csv(f'datos_individuales/{pozo}_promedios_diarios.csv', index=False)
            promedios_horarios.to_csv(f'datos_individuales/{pozo}_promedios_horarios.csv', index=False)

            resumen_general.append(resumen)

        resumen_general_df = pd.DataFrame(resumen_general)
        resumen_general_df.to_csv('datos_individuales/resumen_general.csv', index=False)
        print("Resumen general guardado en 'datos_individuales/resumen_general.csv'.")

    except Exception as e:
        print(f"Error general: {e}")
    finally:
        try:
            db_connection.dispose()
            print("Conexión a la base de datos cerrada.")
        except:
            pass

if __name__ == "__main__":
    try:
        while True:
            extract_and_update_data()
            for _ in range(100):
                time.sleep(1)
    except KeyboardInterrupt:
        print("Ejecución interrumpida manualmente.")
