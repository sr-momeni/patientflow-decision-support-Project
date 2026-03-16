from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Live credentials for the Railway MySQL database
URL_DATABASE = 'mysql+pymysql://root:IhVbkPvRTjfmpbqMfzuVXxXZuyOjfBXj@yamabiko.proxy.rlwy.net:10318/ehospital'

engine = create_engine(URL_DATABASE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if __name__ == "__main__":
    from sqlalchemy import text
    try:
        with engine.connect() as connection:
            # Test basic connection
            connection.execute(text("SELECT 1"))
            print("Successfully connected to the database!")
            
            # Print table names
            print("\nTables in 'ehospital' database:")
            result = connection.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            if tables:
                for table in tables:
                    print(f" - {table[0]}")
            else:
                print(" (No tables found)")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
