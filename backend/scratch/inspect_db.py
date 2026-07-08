import sys
import os
from sqlalchemy import create_engine, inspect, text

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
import models

def inspect_db():
    print("Database Inspection Started...")
    inspector = inspect(engine)
    
    # Get table names
    table_names = inspector.get_table_names()
    print(f"Tables found in database: {table_names}\n")
    
    db = SessionLocal()
    try:
        for table_name in table_names:
            print(f"Table: {table_name}")
            # Get columns
            columns = inspector.get_columns(table_name)
            col_details = []
            for col in columns:
                col_details.append(f"{col['name']} ({col['type']})")
            print("  Columns: " + ", ".join(col_details))
            
            # Get row count dynamically using sql query
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"  Row Count: {count}")
                
                # Fetch first 3 rows as example
                if count > 0:
                    rows = db.execute(text(f"SELECT * FROM {table_name} LIMIT 3")).fetchall()
                    print("  Sample Data:")
                    for r in rows:
                        row_dict = r._asdict() if hasattr(r, '_asdict') else dict(r)
                        # Truncate potentially huge fields like embeddings or password hashes for clean output
                        clean_row = {}
                        for k, v in row_dict.items():
                            if k == 'password_hash':
                                clean_row[k] = '[HASHED_PASSWORD]'
                            elif k == 'embedding' and v is not None:
                                clean_row[k] = f"[float array of length {len(v)}]"
                            else:
                                clean_row[k] = v
                        print(f"    {clean_row}")
            except Exception as inner_e:
                print(f"  Error querying table: {inner_e}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error during inspection: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_db()
