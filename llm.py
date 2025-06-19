import httpx
from typing import Any
import database
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import re
import os
from dotenv import load_dotenv
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
async def human_query_to_sql(human_query: str) -> str | None:
    """Convierte una consulta en lenguaje natural a T-SQL usando Deepseek AI."""
    
    database_schema = database.get_schema()

    system_message = f"""
    You are an AI that strictly translates natural language questions into T-SQL queries.
    Do not add any commentary, explanations, or extra details—only return a valid JSON object with the key 'sql_query' containing the SQL query as a string. Do not include any reasoning or comments. Output example: {{"sql_query": "SELECT ..."}}
    If you output anything other than the JSON object, it will be considered an error.
    <schema>
    {database_schema}
    </schema>
    """

    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": human_query}
        ],
        "temperature": 0,
        "max_tokens": 5000
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"Error DeepSeek: {response.status_code} - {response.text}")
        return None

    #print("Response from DeepSeek:", response.json())
    return response.json()["choices"][0]["message"]["content"]

async def build_answer(result: list[dict[str, Any]], human_query: str) -> str | None:
    """Genera una respuesta en lenguaje natural basada en los resultados SQL."""

    system_message = """
    You are an AI that answers strictly based on provided SQL results.
    Return sql answer with a friendly languaje per user.
    """

    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"SQL Result: {result} \nUser Question: {human_query}"}
        ],
        "temperature": 0,
        "max_tokens": 2000
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=30)

    if response.status_code != 200:
        #print(f"Error DeepSeek: {response.status_code} - {response.text}")
        return None

    return response.json()["choices"][0]["message"]["content"]

def generate_plot_from_sql_result(result: list[dict[str, Any]], plot_type: str = "bar", x_key: str = None, y_key: str = None, title: str = "") -> str:
    """
    Genera un gráfico con matplotlib a partir de los resultados SQL y lo retorna como un string base64.
    plot_type: 'bar', 'pie', 'line', etc.
    x_key, y_key: claves de los datos a graficar.
    """
    if not result or not x_key or not y_key:
        return None
    x = [row[x_key] for row in result]
    y = [row[y_key] for row in result]
    plt.figure(figsize=(8,4))
    if plot_type == "bar":
        plt.style.use('ggplot')  # Estilo de matplotlib
        plt.rcParams['font.family'] = 'Arial'  # Cambia la fuente a Arial
        plt.bar(x, y)
    elif plot_type == "pie":
        plt.pie(y, labels=x, autopct='%1.1f%%')
    elif plot_type == "line":
        plt.plot(x, y, marker='o')
    else:
        return None
    plt.title(title or f"{plot_type.title()} Chart")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

def user_requests_plot(human_query: str) -> bool:
    """Detecta si el usuario solicita un gráfico en su pregunta."""
    keywords = [
        'grafica', 'gráfico', 'gráfica', 'plot', 'chart', 'diagrama', 'visualiza', 'visualización', 'barras', 'línea', 'pie', 'pastel'
    ]
    pattern = re.compile(r'(' + '|'.join(keywords) + r')', re.IGNORECASE)
    return bool(pattern.search(human_query))
