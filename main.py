import json
from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database
import llm
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PostHumanQueryPayload(BaseModel):
    human_query: str
    plot_type: str | None = None
    
class PostHumanQueryResponse(BaseModel):
    result: list
    
def limpiar_json_envoltura(texto: str) -> str:
    """
    Elimina las envolturas ```json al inicio y ``` al final de un bloque de texto.
    """
    texto = texto.strip()
    if texto.startswith("```json"):
        texto = texto[len("```json"):].lstrip()
    if texto.endswith("```"):
        texto = texto[:-3].rstrip()
    return texto


@app.post(
    "/human_query",
    name="Human Query",
    operation_id="post_human_query",
    description="""Gets a natural language query, internally transforms it to a SQL query, queries the database, and returns the result.""",)
async def human_query(payload: PostHumanQueryPayload) -> dict[str, str]:
    sql_query = await llm.human_query_to_sql(payload.human_query)
    print(sql_query)
    sql_query = limpiar_json_envoltura(sql_query)
    if not sql_query:
        return{"error": "failed to generate SQL query"}
    result_dict = json.loads(sql_query)
    result = await database.query(result_dict["sql_query"])
    answer = await llm.build_answer(result, payload.human_query)
    if not answer:
        return{"error": "Failed to generate answer"}
    # Si el usuario seleccionó un tipo de gráfico
    if payload.plot_type:
        x_key, y_key = None, None
        if result and isinstance(result, list) and len(result) > 0:
            keys = list(result[0].keys())
            if len(keys) >= 2:
                x_key, y_key = keys[0], keys[1]
        image_base64 = None
        if x_key and y_key:
            image_base64 = llm.generate_plot_from_sql_result(result, plot_type=payload.plot_type, x_key=x_key, y_key=y_key, title=payload.human_query)
        return {"answer": answer, "image_base64": image_base64}
    # Si no se pide gráfico, solo respuesta textual
    return{"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
