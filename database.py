from typing import Any
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import dotenv
# Cargar las variables de entorno desde el archivo .env
dotenv.load_dotenv()

username = dotenv.get_key('.env', 'username')
password = dotenv.get_key('.env', 'password')
server = dotenv.get_key('.env', 'server')
database = dotenv.get_key('.env', 'database')
engine = create_engine(f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server')
session = sessionmaker(bind=engine)

def get_schema() -> str:
   inspector = inspect(engine)
   table_names = inspector.get_view_names()
   
   def get_column_names(table_name) -> list[str]:
      columns = inspector.get_columns(table_name)
      return [col['name'] for col in columns]
   
   schema_info = []
   for table_name in table_names:
      columns = get_column_names(table_name)
      table_info = f"Table: {table_name}\nColumns: {', '.join(columns)}"
      schema_info.append(table_info)
         
   engine.dispose() 
   #print(schema_info)       
   return "\n\n".join(schema_info)

async def query(sql_query: str) -> list[dict[str, Any]]:
   print("sql_query", sql_query)
   try:
      with session() as sess:
         statement = text(sql_query)
         result = sess.execute(statement)
         return [dict(row._mapping) for row in result]
   except Exception as e:
      print(f"Error ejecutando la consulta: {e}")
      return []
   
def cleaup() -> None:
   engine.dispose()