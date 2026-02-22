from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Hardcoded credentials from eHospital-main/backend/database.py
URL_DATABASE = 'mysql+pymysql://root:password@yamabiko.proxy.rlwy.net:10318/ehospital'

engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
