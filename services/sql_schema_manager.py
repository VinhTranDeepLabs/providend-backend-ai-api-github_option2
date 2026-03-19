import json
import logging
from typing import Dict, Any, List
from utils.azure_db_utils import get_readonly_azure_postgres_connection

logger = logging.getLogger(__name__)

class DatabaseSchemaManager:
    """
    Extracts the database schema (Tables, Columns, Data Types, Foreign Keys)
    from Azure PostgreSQL to feed into the SQL Agent LLM Prompt.
    """
    
    def __init__(self):
        pass

    def get_database_schema_context(self) -> Dict[str, Any]:
        """
        Connects to the database and extracts the schema.
        Returns a dictionary representing the schema structure.
        """
        schema_dict = {"tables": []}
        conn = None
        try:
            conn = get_readonly_azure_postgres_connection()
            cursor = conn.cursor()
            
            # 1. Get all public tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # 2. Extract schema for each table
            for table in tables:
                table_info = {"name": table, "columns": []}
                
                # Get columns
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))
                
                columns = cursor.fetchall()
                for col_name, data_type, is_nullable, column_default in columns:
                    col_info = {
                        "name": col_name,
                        "type": data_type,
                        "nullable": True if is_nullable == 'YES' else False
                    }
                    if column_default:
                        col_info["default"] = str(column_default)
                    table_info["columns"].append(col_info)
                
                # Fetch a sample row to help the LLM understand data formats (like IDs vs UUIDs)
                try:
                    cursor.execute(f'SELECT * FROM "public"."{table}" LIMIT 1;')
                    sample_row = cursor.fetchone()
                    if sample_row:
                        col_names = [desc[0] for desc in cursor.description]
                        sample_dict = {k: str(v) for k, v in zip(col_names, sample_row) if v is not None}
                        table_info["sample_row"] = sample_dict
                except Exception as e:
                    # Table might be empty or restricted
                    conn.rollback()
                    pass
                
                schema_dict["tables"].append(table_info)

            # 3. Get Foreign Keys
            cursor.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
            """)
            
            fk_list = cursor.fetchall()
            schema_dict["foreign_keys"] = []
            for t_name, c_name, ft_name, fc_name in fk_list:
                schema_dict["foreign_keys"].append({
                    "from": f"{t_name}.{c_name}",
                    "to": f"{ft_name}.{fc_name}"
                })
                
            cursor.close()
            return schema_dict
            
        except Exception as e:
            logger.error(f"Error extracting schema context: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_schema_as_string(self) -> str:
        """
        Returns a compressed string representation of the schema for injection into LLM prompt.
        """
        schema_dict = self.get_database_schema_context()
        return json.dumps(schema_dict, indent=2)

    def get_schema_as_natural_language(self) -> str:
        """
        Converts the database schema into detailed, natural language strings.
        This provides a much higher semantic context for the LLM to understand tables and relationships.
        """
        schema_dict = self.get_database_schema_context()
        
        # Manually curated descriptions for typical tables to enhance AI context
        # In a real enterprise system, this could come from a metadata catalog.
        table_descriptions = {
            "advisors": "Contains information about financial advisors providing services.",
            "clients": "Contains personal and primary contact information of individual clients.",
            "meetings": "Log of scheduled or completed advisory meetings between advisors and clients.",
            "meeting_details": "Detailed transcripts, topics, and actionable notes of specific meetings. CRITICAL: The 'client_preferences' column contains a structured JSON string detailing 19 categories of the client's personal preferences, hobbies, sports, family, and lifestyle.",
            "chat": "Tracks conversation/chat sessions in the application.",
            "message": "Individual messages inside a chat session, logging the exact User and AI dialogues.",
            "alembic_version": "Internal track of database migration versions (ignore this for analytics)."
        }
        
        lines = []
        lines.append("Tables available:\n")
        
        for i, table in enumerate(schema_dict["tables"], 1):
            table_name = table["name"]
            desc = table_descriptions.get(table_name, f"Contains information about {table_name}.")
            
            lines.append(f"{i}. {table_name.upper()} DATA")
            lines.append(f"- Table: public.{table_name}")
            lines.append(f"  Description: {desc}")
            lines.append("  columns: [")
            
            col_lines = []
            for col in table["columns"]:
                col_name = col["name"]
                col_type = col["type"]
                null_str = "nullable" if col["nullable"] else "NOT NULL"
                
                # Annotate primary key for context
                is_pk = ""
                if col_name == "id":
                    is_pk = "PRIMARY KEY; "
                    
                # Add descriptions for columns if possible
                col_desc = "Identifying attribute"
                if "id" in col_name and col_name != "id":
                    col_desc = f"Foreign Key relationship Reference"
                elif col_name == "created_at":
                    col_desc = "Timestamp of record creation"
                elif col_type in ['varchar', 'text']:
                    col_desc = "Text data (Use ILIKE '%keyword%' to search)"
                    
                col_lines.append(f"      {col_name} ({col_type}, {null_str}) - {is_pk}{col_desc}")
            
            # Join columns with commas
            lines.append(",\n".join(col_lines))
            lines.append("  ]\n")
            
        # Optional: Append relationships explicitly
        if schema_dict.get("foreign_keys"):
            lines.append("RELATIONSHIPS:")
            for idx, fk in enumerate(schema_dict["foreign_keys"], 1):
                lines.append(f"{idx}. {fk['from']} references {fk['to']}")
                
        return "\n".join(lines)

if __name__ == "__main__":
    # Test script locally
    manager = DatabaseSchemaManager()
    
    print("--- JSON SCHEMA ---")
    schema_str = manager.get_schema_as_string()
    print("Extracted Schema Length:", len(schema_str))
    
    print("\n--- NATURAL LANGUAGE SCHEMA ---")
    nl_schema_str = manager.get_schema_as_natural_language()
    print("Natural Language Schema Length:", len(nl_schema_str))
    print("Preview:")
    print(nl_schema_str[:1000] + "\n...[TRUNCATED]")
