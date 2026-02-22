from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

URL_DATABASE = 'mysql+pymysql://root:password@yamabiko.proxy.rlwy.net:10318/ehospital'
#password
engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)