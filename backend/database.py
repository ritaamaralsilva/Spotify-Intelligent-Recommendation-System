import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Lê a URL da base de dados do ficheiro .env
DATABASE_URL = os.getenv("DATABASE_URL")

# O engine é o motor que gere as ligações à base de dados
# pool_pre_ping=True é vital para a Azure, pois evita que a ligação caia por inatividade
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True
)

# Criamos uma fábrica de sessões (cada pedido ao FastAPI terá a sua própria sessão)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Esta será a classe base que todas as nossas tabelas (modelos) vão herdar
Base = declarative_base()

# Dependência que as rotas do FastAPI vão usar para abrir/fechar o acesso à BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()