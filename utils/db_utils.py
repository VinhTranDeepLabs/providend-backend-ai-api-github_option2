import psycopg2
from psycopg2 import Error
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, date
from decimal import Decimal

class DatabaseUtils:
    """Utility class for CRUD operations on advisors, clients, meetings, meeting_details, products, and client_products tables"""
    
    def __init__(self, connection):
        self.conn = connection
    
    # ==================== ADVISOR OPERATIONS ====================
    
    def create_advisor(self, advisor_id: str, name: str, email: str = None, role: str = None) -> Dict:
        """Create a new advisor"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO advisors (advisor_id, name, email, role, date_created)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING *;
            """
            cursor.execute(query, (advisor_id, name, email, role))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Advisor created successfully", "advisor_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating advisor: {e}"}
    
    def get_advisor(self, advisor_id: str) -> Optional[Dict]:
        """Get advisor profile by ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM advisors WHERE advisor_id = %s;"
            cursor.execute(query, (advisor_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "advisor_id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "role": result[3],
                    "date_created": result[4]
                }
            return None
        except Error as e:
            print(f"Error fetching advisor: {e}")
            return None
    
    def update_advisor(self, advisor_id: str, name: str = None, email: str = None, role: str = None) -> Dict:
        """Update advisor details"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if name:
                updates.append("name = %s")
                params.append(name)
            if email:
                updates.append("email = %s")
                params.append(email)
            if role:
                updates.append("role = %s")
                params.append(role)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            params.append(advisor_id)
            query = f"UPDATE advisors SET {', '.join(updates)} WHERE advisor_id = %s;"
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Advisor updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating advisor: {e}"}
    
    def delete_advisor(self, advisor_id: str) -> Dict:
        """Delete an advisor"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM advisors WHERE advisor_id = %s;"
            cursor.execute(query, (advisor_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Advisor deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting advisor: {e}"}
    
    def list_advisors(self) -> List[Dict]:
        """List all advisors"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM advisors ORDER BY name;"
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            advisors = []
            for row in results:
                advisors.append({
                    "advisor_id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "role": row[3],
                    "date_created": row[4]
                })
            return advisors
        except Error as e:
            print(f"Error listing advisors: {e}")
            return []
    
    # ==================== CLIENT OPERATIONS ====================
    
    def create_client(self, client_id: str, name: str, advisor_id: str = None, 
                     current_recommendation: str = None, status: str = None) -> Dict:
        """Create a new client"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO clients (client_id, name, advisor_id, current_recommendation, date_created, status)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING *;
            """
            cursor.execute(query, (client_id, name, advisor_id, current_recommendation, status))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Client created successfully", "client_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating client: {e}"}
    
    def get_client(self, client_id: str) -> Optional[Dict]:
        """Get client profile by ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM clients WHERE client_id = %s;"
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "client_id": result[0],
                    "name": result[1],
                    "advisor_id": result[2],
                    "current_recommendation": result[3],
                    "date_created": result[4],
                    "status": result[5]
                }
            return None
        except Error as e:
            print(f"Error fetching client: {e}")
            return None
    
    def update_client(self, client_id: str, name: str = None, advisor_id: str = None,
                     current_recommendation: str = None, status: str = None) -> Dict:
        """Update client details"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if name:
                updates.append("name = %s")
                params.append(name)
            if advisor_id:
                updates.append("advisor_id = %s")
                params.append(advisor_id)
            if current_recommendation is not None:
                updates.append("current_recommendation = %s")
                params.append(current_recommendation)
            if status:
                updates.append("status = %s")
                params.append(status)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            params.append(client_id)
            query = f"UPDATE clients SET {', '.join(updates)} WHERE client_id = %s;"
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Client updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating client: {e}"}
    
    def delete_client(self, client_id: str) -> Dict:
        """Delete a client"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM clients WHERE client_id = %s;"
            cursor.execute(query, (client_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Client deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting client: {e}"}
    
    def list_clients(self, advisor_id: str = None) -> List[Dict]:
        """List all clients or clients by advisor"""
        try:
            cursor = self.conn.cursor()
            if advisor_id:
                query = "SELECT * FROM clients WHERE advisor_id = %s ORDER BY name;"
                cursor.execute(query, (advisor_id,))
            else:
                query = "SELECT * FROM clients ORDER BY name;"
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            clients = []
            for row in results:
                clients.append({
                    "client_id": row[0],
                    "name": row[1],
                    "advisor_id": row[2],
                    "current_recommendation": row[3],
                    "date_created": row[4],
                    "status": row[5]
                })
            return clients
        except Error as e:
            print(f"Error listing clients: {e}")
            return []
    
    # ==================== MEETING OPERATIONS ====================
    
    def create_meeting(self, meeting_id: str, client_id: str, advisor_id: str, 
                    meeting_name: str = None, meeting_type: str = None, 
                    status: str = "Started") -> Dict:
        """Create a new meeting"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO meetings (meeting_id, client_id, advisor_id, meeting_type, created_datetime, status, meeting_name)
                VALUES (%s, %s, %s, %s, NOW(), %s, %s)
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, client_id, advisor_id, meeting_type, status, meeting_name))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting created successfully", "meeting_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating meeting: {e}"}
        
    def create_quick_meeting(self, meeting_id: str, advisor_id: str, 
                            meeting_name: str = None, meeting_type: str = None, 
                            status: str = "Started") -> Dict:
        """Create a new quick meeting without client_id (can be assigned later)"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO meetings (meeting_id, client_id, advisor_id, meeting_type, created_datetime, status, meeting_name)
                VALUES (%s, NULL, %s, %s, NOW(), %s, %s)
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, advisor_id, meeting_type, status, meeting_name))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Quick meeting created successfully", "meeting_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating quick meeting: {e}"}
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict]:
        """Get meeting by meeting ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM meetings WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                return {
                    "meeting_id": result[0],
                    "client_id": result[1],
                    "advisor_id": result[2],
                    "meeting_type": result[3],
                    "created_datetime": result[4],
                    "status": result[5],
                    "meeting_name": result[6],
                }
            return None
        except Error as e:
            print(f"Error fetching meeting: {e}")
            return None
    
    def update_meeting(self, meeting_id: str, client_id: str = None, advisor_id: str = None,
                  meeting_name: str = None, meeting_type: str = None, 
                  status: str = None) -> Dict:
        """Update meeting details"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if client_id:
                updates.append("client_id = %s")
                params.append(client_id)
            if advisor_id:
                updates.append("advisor_id = %s")
                params.append(advisor_id)
            if meeting_name is not None:
                updates.append("meeting_name = %s")
                params.append(meeting_name)
            if meeting_type:
                updates.append("meeting_type = %s")
                params.append(meeting_type)
            if status:
                updates.append("status = %s")
                params.append(status)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            params.append(meeting_id)
            query = f"UPDATE meetings SET {', '.join(updates)} WHERE meeting_id = %s;"
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating meeting: {e}"}
    
    def delete_meeting(self, meeting_id: str) -> Dict:
        """Delete a meeting"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM meetings WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting meeting: {e}"}
    
    def list_meetings(self, client_id: str = None, advisor_id: str = None) -> List[Dict]:
        """List meetings filtered by client_id or advisor_id"""
        try:
            cursor = self.conn.cursor()
            if client_id:
                query = "SELECT * FROM meetings WHERE client_id = %s ORDER BY created_datetime DESC;"
                cursor.execute(query, (client_id,))
            elif advisor_id:
                query = "SELECT * FROM meetings WHERE advisor_id = %s ORDER BY created_datetime DESC;"
                cursor.execute(query, (advisor_id,))
            else:
                query = "SELECT * FROM meetings ORDER BY created_datetime DESC;"
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            meetings = []
            for row in results:
                meetings.append({
                    "meeting_id": row[0],
                    "client_id": row[1],
                    "advisor_id": row[2],
                    "meeting_type": row[3],
                    "created_datetime": row[4],
                    "status": row[5],
                    "meeting_name": row[6],
                })
            return meetings
        except Error as e:
            print(f"Error listing meetings: {e}")
            return []
        
    def list_meetings_paginated(
        self,
        advisor_id: str,
        search: str = None,
        meeting_types: List[str] = None,
        date_from: str = None,
        date_to: str = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        List meetings with pagination, search, filtering, and sorting
        
        Args:
            advisor_id: Advisor ID to filter meetings
            search: Search term for client_name, meeting_name, or meeting_type
            meeting_types: List of meeting types to filter (OR logic)
            date_from: Start date filter (ISO format: YYYY-MM-DD)
            date_to: End date filter (ISO format: YYYY-MM-DD)
            sort_by: Field to sort by ('date' or 'client_name')
            sort_order: Sort order ('asc' or 'desc')
            page: Page number (1-indexed)
            per_page: Number of records per page
        
        Returns:
            Dict with 'data' (list of meetings) and 'pagination' (metadata)
        """
        try:
            cursor = self.conn.cursor()
            
            # Base WHERE clause
            where_clauses = ["m.advisor_id = %s"]
            params = [advisor_id]
            
            # Search filter (case-insensitive partial match)
            if search:
                search_clause = """(
                    LOWER(c.name) LIKE LOWER(%s) OR 
                    LOWER(m.meeting_name) LIKE LOWER(%s) OR 
                    LOWER(m.meeting_type) LIKE LOWER(%s)
                )"""
                where_clauses.append(search_clause)
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            # Meeting type filter (multiple values with OR logic)
            if meeting_types and len(meeting_types) > 0:
                placeholders = ','.join(['%s'] * len(meeting_types))
                where_clauses.append(f"m.meeting_type IN ({placeholders})")
                params.extend(meeting_types)
            
            # Date range filter
            if date_from:
                where_clauses.append("m.created_datetime >= %s")
                params.append(date_from)
            
            if date_to:
                # Include the entire end date (up to 23:59:59)
                where_clauses.append("m.created_datetime < %s::date + interval '1 day'")
                params.append(date_to)
            
            # Build WHERE clause
            where_sql = " AND ".join(where_clauses)
            
            # Count total records
            count_query = f"""
                SELECT COUNT(*)
                FROM meetings m
                LEFT JOIN clients c ON m.client_id = c.client_id
                WHERE {where_sql};
            """
            cursor.execute(count_query, params)
            total_records = cursor.fetchone()[0]
            
            # Calculate pagination
            total_pages = (total_records + per_page - 1) // per_page  # Ceiling division
            
            # Ensure page doesn't exceed total_pages
            if page > total_pages and total_pages > 0:
                page = total_pages
            
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Determine ORDER BY clause
            if sort_by == "client_name":
                # Handle NULL client_id (quick meetings) - put them last
                order_by = f"c.name {sort_order.upper()} NULLS LAST"
            else:  # sort_by == "date"
                order_by = f"m.created_datetime {sort_order.upper()}"
            
            # Build main query
            select_query = f"""
                SELECT 
                    m.meeting_id,
                    m.client_id,
                    c.name as client_name,
                    m.advisor_id,
                    m.meeting_name,
                    m.meeting_type,
                    m.created_datetime,
                    m.status
                FROM meetings m
                LEFT JOIN clients c ON m.client_id = c.client_id
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s;
            """
            
            cursor.execute(select_query, params + [per_page, offset])
            results = cursor.fetchall()
            cursor.close()
            
            # Format results
            meetings = []
            for row in results:
                meetings.append({
                    "meeting_id": row[0],
                    "client_id": row[1],
                    "client_name": row[2],
                    "advisor_id": row[3],
                    "meeting_name": row[4],
                    "meeting_type": row[5],
                    "created_datetime": row[6],
                    "status": row[7]
                })
            
            # Build pagination metadata
            pagination = {
                "current_page": page,
                "per_page": per_page,
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
            
            return {
                "success": True,
                "data": meetings,
                "pagination": pagination
            }
            
        except Error as e:
            print(f"Error listing paginated meetings: {e}")
            return {
                "success": False,
                "data": [],
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_records": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                },
                "error": str(e)
            }
    
    # ==================== MEETING DETAILS OPERATIONS ====================
    
    def create_meeting_detail(self, meeting_id: str, transcript: str = None, summary: str = None,
                         recommendations: str = None, questions: str = None, 
                         advisor_notes: str = None, question_tracker: str = None) -> Dict:
        """Create meeting details"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO meeting_details (meeting_id, transcript, summary, recommendations, questions, advisor_notes, question_tracker, updated_datetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, transcript, summary, recommendations, questions, advisor_notes, question_tracker))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting details created successfully", "meeting_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating meeting details: {e}"}
    
    def get_meeting_detail(self, meeting_id: str) -> Optional[Dict]:
        """Get meeting details by meeting ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM meeting_details WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            meeting = cursor.fetchone()
            query = "SELECT * FROM meetings WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            details = cursor.fetchone()
            cursor.close()
            
            if meeting:
                if meeting:
                    return {
                        "meeting_id": meeting[0],
                        "transcript": meeting[1],
                        "summary": meeting[2],
                        "recommendations": meeting[3],
                        "questions": meeting[4],
                        "advisor_notes": meeting[5],
                        "updated_datetime": meeting[6],
                        "processing_status": meeting[7],
                        "processing_retry_count": meeting[8],
                        "processing_error": meeting[9],
                        "question_tracker": meeting[10],
                        "meeting_name": details[6],
                    }

            return None
        except Error as e:
            print(f"Error fetching meeting details: {e}")
            return None
    
    def update_meeting_detail(self, meeting_id: str, transcript: str = None, summary: str = None,
                        recommendations: str = None, questions: str = None,
                        advisor_notes: str = None, question_tracker: str = None,
                        processing_status: str = None,           # ← ADD
                        processing_retry_count: int = None,      # ← ADD
                        processing_error: str = None) -> Dict:   # ← ADD
        """Update meeting details"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if transcript is not None:
                updates.append("transcript = %s")
                params.append(transcript)
            if summary is not None:
                updates.append("summary = %s")
                params.append(summary)
            if recommendations is not None:
                updates.append("recommendations = %s")
                params.append(recommendations)
            if questions is not None:
                updates.append("questions = %s")
                params.append(questions)
            if advisor_notes is not None:
                updates.append("advisor_notes = %s")
                params.append(advisor_notes)
            if question_tracker is not None:
                updates.append("question_tracker = %s")
                params.append(question_tracker)
            
            # ← ADD THESE
            if processing_status is not None:
                updates.append("processing_status = %s")
                params.append(processing_status)
            if processing_retry_count is not None:
                updates.append("processing_retry_count = %s")
                params.append(processing_retry_count)
            if processing_error is not None:
                updates.append("processing_error = %s")
                params.append(processing_error)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            updates.append("updated_datetime = NOW()")
            
            params.append(meeting_id)
            query = f"UPDATE meeting_details SET {', '.join(updates)} WHERE meeting_id = %s;"
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting details updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating meeting details: {e}"}
    
    def delete_meeting_detail(self, meeting_id: str) -> Dict:
        """Delete meeting details"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM meeting_details WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting details deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting meeting details: {e}"}
    
    def list_meeting_details(self, meeting_ids: List[str] = None) -> List[Dict]:
        """List all meeting details or specific meeting IDs"""
        try:
            cursor = self.conn.cursor()
            if meeting_ids:
                query = "SELECT * FROM meeting_details WHERE meeting_id = ANY(%s);"
                cursor.execute(query, (meeting_ids,))
            else:
                query = "SELECT * FROM meeting_details ORDER BY updated_datetime DESC;"
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            details = []
            details = []
            for row in results:
                details.append({
                    "meeting_id": row[0],
                    "transcript": row[1],
                    "summary": row[2],
                    "recommendations": row[3],
                    "questions": row[4],
                    "advisor_notes": row[5],
                    "question_tracker": row[6],
                    "updated_datetime": row[7]
                })
            return details
        except Error as e:
            print(f"Error listing meeting details: {e}")
            return []
    
    # ==================== PRODUCT OPERATIONS ====================
    
    def create_product(self, product_id: str, name: str, type: str = None, 
                      description: str = None, risk_level: str = None) -> Dict:
        """Create a new product"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO products (product_id, name, type, description, risk_level, date_created)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING *;
            """
            cursor.execute(query, (product_id, name, type, description, risk_level))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Product created successfully", "product_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating product: {e}"}
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product by ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM products WHERE product_id = %s;"
            cursor.execute(query, (product_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "product_id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "description": result[3],
                    "risk_level": result[4],
                    "date_created": result[5]
                }
            return None
        except Error as e:
            print(f"Error fetching product: {e}")
            return None
    
    def update_product(self, product_id: str, name: str = None, type: str = None,
                      description: str = None, risk_level: str = None) -> Dict:
        """Update product details"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if name:
                updates.append("name = %s")
                params.append(name)
            if type:
                updates.append("type = %s")
                params.append(type)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if risk_level:
                updates.append("risk_level = %s")
                params.append(risk_level)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            params.append(product_id)
            query = f"UPDATE products SET {', '.join(updates)} WHERE product_id = %s;"
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Product updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating product: {e}"}
    
    def delete_product(self, product_id: str) -> Dict:
        """Delete a product"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM products WHERE product_id = %s;"
            cursor.execute(query, (product_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Product deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting product: {e}"}
    
    def list_products(self) -> List[Dict]:
        """List all products"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM products ORDER BY name;"
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            products = []
            for row in results:
                products.append({
                    "product_id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "description": row[3],
                    "risk_level": row[4],
                    "date_created": row[5]
                })
            return products
        except Error as e:
            print(f"Error listing products: {e}")
            return []
    
    # ==================== CLIENT_PRODUCTS OPERATIONS ====================
    
    def add_product_to_client(self, client_id: str, product_id: str, 
                             purchase_date: date = None, status: str = None,
                             investment_amount: Decimal = None) -> Dict:
        """Link a product to a client (add to client_products junction table)"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO client_products (client_id, product_id, purchase_date, status, investment_amount)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (client_id, product_id) DO UPDATE
                SET purchase_date = EXCLUDED.purchase_date,
                    status = EXCLUDED.status,
                    investment_amount = EXCLUDED.investment_amount
                RETURNING *;
            """
            cursor.execute(query, (client_id, product_id, purchase_date, status, investment_amount))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Product added to client successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error adding product to client: {e}"}
    
    def remove_product_from_client(self, client_id: str, product_id: str) -> Dict:
        """Remove a product from a client"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM client_products WHERE client_id = %s AND product_id = %s;"
            cursor.execute(query, (client_id, product_id))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Product removed from client successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error removing product from client: {e}"}
    
    def get_client_products(self, client_id: str) -> List[Dict]:
        """Get all products for a client with details"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT cp.client_id, cp.product_id, cp.purchase_date, cp.status, cp.investment_amount,
                       p.name, p.type, p.description, p.risk_level
                FROM client_products cp
                JOIN products p ON cp.product_id = p.product_id
                WHERE cp.client_id = %s
                ORDER BY cp.purchase_date DESC;
            """
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            cursor.close()
            
            products = []
            for row in results:
                products.append({
                    "client_id": row[0],
                    "product_id": row[1],
                    "purchase_date": row[2],
                    "status": row[3],
                    "investment_amount": row[4],
                    "product_name": row[5],
                    "product_type": row[6],
                    "product_description": row[7],
                    "risk_level": row[8]
                })
            return products
        except Error as e:
            print(f"Error fetching client products: {e}")
            return []
    
    def get_product_clients(self, product_id: str) -> List[Dict]:
        """Get all clients for a product with details"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT cp.client_id, cp.product_id, cp.purchase_date, cp.status, cp.investment_amount,
                       c.name, c.advisor_id
                FROM client_products cp
                JOIN clients c ON cp.client_id = c.client_id
                WHERE cp.product_id = %s
                ORDER BY cp.purchase_date DESC;
            """
            cursor.execute(query, (product_id,))
            results = cursor.fetchall()
            cursor.close()
            
            clients = []
            for row in results:
                clients.append({
                    "client_id": row[0],
                    "product_id": row[1],
                    "purchase_date": row[2],
                    "status": row[3],
                    "investment_amount": row[4],
                    "client_name": row[5],
                    "advisor_id": row[6]
                })
            return clients
        except Error as e:
            print(f"Error fetching product clients: {e}")
            return []
    
    # ==================== TRANSCRIPT AGGREGATOR OPERATIONS ====================
    
    def add_transcript_segment(self, meeting_id: str, transcript: str, 
                              start_datetime: datetime = None) -> Dict:
        """
        Add a transcript segment to the transcript_aggregator table.
        
        Args:
            meeting_id: The meeting ID (FK)
            transcript: The transcript text segment
            start_datetime: When this segment was captured (defaults to NOW)
        
        Returns:
            Dict with success status and segment index
        """
        try:
            cursor = self.conn.cursor()
            
            if start_datetime is None:
                query = """
                    INSERT INTO transcript_aggregator (meeting_id, transcript, start_datetime)
                    VALUES (%s, %s, NOW())
                    RETURNING index, meeting_id, transcript, start_datetime;
                """
                cursor.execute(query, (meeting_id, transcript))
            else:
                query = """
                    INSERT INTO transcript_aggregator (meeting_id, transcript, start_datetime)
                    VALUES (%s, %s, %s)
                    RETURNING index, meeting_id, transcript, start_datetime;
                """
                cursor.execute(query, (meeting_id, transcript, start_datetime))
            
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True, 
                "message": "Transcript segment added successfully",
                "segment_index": result[0],
                "meeting_id": result[1],
                "start_datetime": result[3]
            }
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error adding transcript segment: {e}"}
    
    def get_transcript_segments(self, meeting_id: str) -> List[Dict]:
        """
        Get all transcript segments for a meeting, ordered by index.
        
        Args:
            meeting_id: The meeting ID
        
        Returns:
            List of transcript segments
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT index, meeting_id, transcript, start_datetime
                FROM transcript_aggregator
                WHERE meeting_id = %s
                ORDER BY index ASC;
            """
            cursor.execute(query, (meeting_id,))
            results = cursor.fetchall()
            cursor.close()
            
            segments = []
            for row in results:
                segments.append({
                    "index": row[0],
                    "meeting_id": row[1],
                    "transcript": row[2],
                    "start_datetime": row[3]
                })
            return segments
        except Error as e:
            print(f"Error fetching transcript segments: {e}")
            return []
    
    def get_transcript_segment_by_index(self, meeting_id: str, segment_index: int) -> Optional[Dict]:
        """
        Get a specific transcript segment by its index.
        
        Args:
            meeting_id: The meeting ID
            segment_index: The segment index
        
        Returns:
            Transcript segment or None
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT index, meeting_id, transcript, start_datetime
                FROM transcript_aggregator
                WHERE meeting_id = %s AND index = %s;
            """
            cursor.execute(query, (meeting_id, segment_index))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "index": result[0],
                    "meeting_id": result[1],
                    "transcript": result[2],
                    "start_datetime": result[3]
                }
            return None
        except Error as e:
            print(f"Error fetching transcript segment: {e}")
            return None
    
    def get_transcript_segments_by_time(self, meeting_id: str, 
                                       start_time: datetime = None, 
                                       end_time: datetime = None) -> List[Dict]:
        """
        Get transcript segments within a time range.
        
        Args:
            meeting_id: The meeting ID
            start_time: Start datetime (optional)
            end_time: End datetime (optional)
        
        Returns:
            List of transcript segments within time range
        """
        try:
            cursor = self.conn.cursor()
            
            # Build query based on time parameters
            if start_time and end_time:
                query = """
                    SELECT index, meeting_id, transcript, start_datetime
                    FROM transcript_aggregator
                    WHERE meeting_id = %s AND start_datetime BETWEEN %s AND %s
                    ORDER BY index ASC;
                """
                cursor.execute(query, (meeting_id, start_time, end_time))
            elif start_time:
                query = """
                    SELECT index, meeting_id, transcript, start_datetime
                    FROM transcript_aggregator
                    WHERE meeting_id = %s AND start_datetime >= %s
                    ORDER BY index ASC;
                """
                cursor.execute(query, (meeting_id, start_time))
            elif end_time:
                query = """
                    SELECT index, meeting_id, transcript, start_datetime
                    FROM transcript_aggregator
                    WHERE meeting_id = %s AND start_datetime <= %s
                    ORDER BY index ASC;
                """
                cursor.execute(query, (meeting_id, end_time))
            else:
                # No time filters, return all
                return self.get_transcript_segments(meeting_id)
            
            results = cursor.fetchall()
            cursor.close()
            
            segments = []
            for row in results:
                segments.append({
                    "index": row[0],
                    "meeting_id": row[1],
                    "transcript": row[2],
                    "start_datetime": row[3]
                })
            return segments
        except Error as e:
            print(f"Error fetching transcript segments by time: {e}")
            return []
    
    def aggregate_transcripts(self, meeting_id: str, separator: str = "\n") -> Optional[str]:
        """
        Aggregate all transcript segments (JSON arrays) into a single JSON array.
        
        Each segment contains a JSON array like: [{"speaker":"Guest-1","text":"..."}]
        This method merges all segments into one unified JSON array.
        
        Args:
            meeting_id: The meeting ID
            separator: DEPRECATED - kept for backwards compatibility but not used
        
        Returns:
            JSON string containing merged transcript array, or None if no segments found
        """
        import json
        
        segments = self.get_transcript_segments(meeting_id)
        
        if not segments:
            return None
        
        # Merge all JSON arrays into one
        all_entries = []
        
        for segment in segments:
            transcript_json = segment.get("transcript")
            
            if not transcript_json:
                continue
            
            try:
                # Parse each segment's JSON array
                segment_array = json.loads(transcript_json)
                
                # Validate it's a list
                if isinstance(segment_array, list):
                    all_entries.extend(segment_array)
                else:
                    print(f"Warning: Segment is not a JSON array for meeting {meeting_id}")
                    
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse segment JSON for meeting {meeting_id}: {e}")
                continue
        
        if not all_entries:
            return None
        
        # Return as JSON string
        return json.dumps(all_entries)
    
    def update_transcript_segment(self, meeting_id: str, segment_index: int, 
                                 transcript: str = None, 
                                 start_datetime: datetime = None) -> Dict:
        """
        Update a specific transcript segment.
        
        Args:
            meeting_id: The meeting ID
            segment_index: The segment index to update
            transcript: New transcript text (optional)
            start_datetime: New start datetime (optional)
        
        Returns:
            Dict with success status
        """
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if transcript is not None:
                updates.append("transcript = %s")
                params.append(transcript)
            if start_datetime is not None:
                updates.append("start_datetime = %s")
                params.append(start_datetime)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            params.extend([meeting_id, segment_index])
            query = f"""
                UPDATE transcript_aggregator 
                SET {', '.join(updates)} 
                WHERE meeting_id = %s AND index = %s;
            """
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "message": "Transcript segment updated successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating transcript segment: {e}"}
    
    def delete_transcript_segment(self, meeting_id: str, segment_index: int) -> Dict:
        """
        Delete a specific transcript segment.
        
        Args:
            meeting_id: The meeting ID
            segment_index: The segment index to delete
        
        Returns:
            Dict with success status
        """
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM transcript_aggregator WHERE meeting_id = %s AND index = %s;"
            cursor.execute(query, (meeting_id, segment_index))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Transcript segment deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting transcript segment: {e}"}
    
    def delete_transcript_segments(self, meeting_id: str) -> Dict:
        """
        Delete ALL transcript segments for a meeting.
        
        Args:
            meeting_id: The meeting ID
        
        Returns:
            Dict with success status and count of deleted segments
        """
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM transcript_aggregator WHERE meeting_id = %s RETURNING index;"
            cursor.execute(query, (meeting_id,))
            deleted_rows = cursor.fetchall()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True, 
                "message": f"Deleted {len(deleted_rows)} transcript segment(s)",
                "deleted_count": len(deleted_rows)
            }
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting transcript segments: {e}"}
    
    def count_transcript_segments(self, meeting_id: str) -> int:
        """
        Count the number of transcript segments for a meeting.
        
        Args:
            meeting_id: The meeting ID
        
        Returns:
            Number of segments
        """
        try:
            cursor = self.conn.cursor()
            query = "SELECT COUNT(*) FROM transcript_aggregator WHERE meeting_id = %s;"
            cursor.execute(query, (meeting_id,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 0
        except Error as e:
            print(f"Error counting transcript segments: {e}")
            return 0
        

    # ==================== MEETING PROCESSING OPERATIONS ====================
    
    def get_meetings_for_processing(self, limit: int = 10) -> List[Dict]:
        """
        Get meetings ready for AI processing with exponential backoff.
        
        Uses existing 'updated_datetime' field to implement backoff without 
        needing an additional field.
        
        Criteria:
        - meeting.status = 'Completed'
        - meeting_details.transcript IS NOT NULL
        - meeting_details.processing_status = 'pending'
        - Respects exponential backoff for retries using updated_datetime
        
        Args:
            limit: Maximum number of meetings to return
        
        Returns:
            List of meeting dictionaries ready for processing
        """
        try:
            cursor = self.conn.cursor()
            
            # Query meetings ready for processing
            # Uses updated_datetime for exponential backoff:
            # - retry_count 0: immediate
            # - retry_count 1: wait 30s since last update
            # - retry_count 2: wait 60s since last update
            # - retry_count 3+: already marked as 'failed'
            query = """
                SELECT 
                    m.meeting_id,
                    m.client_id,
                    m.advisor_id,
                    m.meeting_type,
                    md.transcript,
                    md.processing_retry_count,
                    md.updated_datetime
                FROM meetings m
                JOIN meeting_details md ON m.meeting_id = md.meeting_id
                WHERE m.status = 'Completed'
                  AND md.transcript IS NOT NULL
                  AND md.processing_status = 'pending'
                  AND (
                    md.processing_retry_count = 0
                    OR md.updated_datetime < NOW() - INTERVAL '1 second' * (30 * POWER(2, md.processing_retry_count - 1))
                  )
                ORDER BY m.created_datetime ASC
                LIMIT %s;
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            
            meetings = []
            for row in results:
                meetings.append({
                    "meeting_id": row[0],
                    "client_id": row[1],
                    "advisor_id": row[2],
                    "meeting_type": row[3],
                    "transcript": row[4],
                    "processing_retry_count": row[5],
                    "updated_datetime": row[6]
                })
            
            return meetings
            
        except Error as e:
            print(f"Error getting meetings for processing: {e}")
            return []
    
    def claim_meeting_for_processing(self, meeting_id: str) -> bool:
        """
        Attempt to claim a meeting for processing using optimistic locking.
        
        This prevents multiple processor instances from working on the same meeting.
        Updates updated_datetime automatically via database default.
        
        Args:
            meeting_id: The meeting ID to claim
        
        Returns:
            True if successfully claimed, False if already being processed
        """
        try:
            cursor = self.conn.cursor()
            
            # Optimistic lock: only update if still in 'pending' status
            # updated_datetime will be set to NOW() automatically
            query = """
                UPDATE meeting_details
                SET processing_status = 'processing',
                    updated_datetime = NOW()
                WHERE meeting_id = %s
                  AND processing_status = 'pending'
                RETURNING meeting_id;
            """
            
            cursor.execute(query, (meeting_id,))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            # If no rows were updated, another process claimed it
            if result is None:
                return False
            
            return True
            
        except Error as e:
            self.conn.rollback()
            print(f"Error claiming meeting for processing: {e}")
            return False
    
    def save_processing_results(self, meeting_id: str, questions: str = None, 
                               summary: str = None, recommendations: str = None) -> Dict:
        """
        Save successful processing results and mark as completed.
        
        Args:
            meeting_id: The meeting ID
            questions: Autofilled questions JSON string
            summary: Generated summary text
            recommendations: Product recommendations JSON string
        
        Returns:
            Dict with success status
        """
        try:
            cursor = self.conn.cursor()
            
            updates = []
            params = []
            
            if questions is not None:
                updates.append("questions = %s")
                params.append(questions)
            
            if summary is not None:
                updates.append("summary = %s")
                params.append(summary)

            if recommendations is not None:
                updates.append("recommendations = %s")
                params.append(recommendations)
            
            # Always update processing fields and updated_datetime
            updates.extend([
                "processing_status = %s",
                "processing_error = NULL",
                "updated_datetime = NOW()"
            ])
            params.append("completed")
            params.append(meeting_id)
            
            query = f"""
                UPDATE meeting_details
                SET {', '.join(updates)}
                WHERE meeting_id = %s;
            """
            
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": "Processing results saved successfully"
            }
            
        except Error as e:
            self.conn.rollback()
            return {
                "success": False,
                "message": f"Error saving processing results: {e}"
            }
    
    def mark_processing_failed(self, meeting_id: str, error_msg: str, 
                              retry_count: int, max_retries: int = 3) -> Dict:
        """
        Mark processing as failed and handle retry logic.
        
        Updates updated_datetime to implement exponential backoff on next retry.
        
        Args:
            meeting_id: The meeting ID
            error_msg: Error message to store
            retry_count: Current retry count
            max_retries: Maximum retries before giving up
        
        Returns:
            Dict with success status and whether to retry
        """
        try:
            cursor = self.conn.cursor()
            
            new_retry_count = retry_count + 1
            
            if new_retry_count >= max_retries:
                # Give up after max retries
                status = "failed"
                message = f"Processing failed after {max_retries} attempts"
            else:
                # Set back to pending for retry
                # updated_datetime = NOW() will be used for backoff calculation
                status = "pending"
                message = f"Processing failed, will retry (attempt {new_retry_count + 1}/{max_retries})"
            
            query = """
                UPDATE meeting_details
                SET processing_status = %s,
                    processing_retry_count = %s,
                    processing_error = %s,
                    updated_datetime = NOW()
                WHERE meeting_id = %s;
            """
            
            cursor.execute(query, (status, new_retry_count, error_msg, meeting_id))
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": message,
                "will_retry": status == "pending",
                "retry_count": new_retry_count
            }
            
        except Error as e:
            self.conn.rollback()
            return {
                "success": False,
                "message": f"Error marking processing as failed: {e}",
                "will_retry": False
            }
        
    # ==================== FEEDBACK OPERATIONS ====================

    def create_feedback(self, meeting_id: str, feedback: str, feedback_on: str = None) -> Dict:
        """Create a new feedback entry"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO feedback (meeting_id, feedback, feedback_on, edit_datetime)
                VALUES (%s, %s, %s, NOW())
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, feedback, feedback_on))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": "Feedback created successfully",
                "feedback_index": result[0],
                "meeting_id": result[1],
                "feedback": result[2],
                "feedback_on": result[3],
                "edit_datetime": result[4]
            }
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating feedback: {e}"}


    # Update get_feedback method to return feedback_on:

    def get_feedback(self, feedback_index: int) -> Optional[Dict]:
        """Get a single feedback entry by index"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM feedback WHERE index = %s;"
            cursor.execute(query, (feedback_index,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "feedback_index": result[0],
                    "meeting_id": result[1],
                    "feedback": result[2],
                    "feedback_on": result[3],  # Add this line
                    "edit_datetime": result[4]
                }
            return None
        except Error as e:
            print(f"Error fetching feedback: {e}")
            return None


    # Update list_feedbacks method to return feedback_on:

    def list_feedbacks(self, meeting_id: str = None) -> List[Dict]:
        """List all feedback entries or filter by meeting_id"""
        try:
            cursor = self.conn.cursor()
            if meeting_id:
                query = "SELECT * FROM feedback WHERE meeting_id = %s ORDER BY edit_datetime DESC;"
                cursor.execute(query, (meeting_id,))
            else:
                query = "SELECT * FROM feedback ORDER BY edit_datetime DESC;"
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            feedbacks = []
            for row in results:
                feedbacks.append({
                    "feedback_index": row[0],
                    "meeting_id": row[1],
                    "feedback": row[2],
                    "feedback_on": row[3],  # Add this line
                    "edit_datetime": row[4]
                })
            return feedbacks
        except Error as e:
            print(f"Error listing feedbacks: {e}")
            return []


    # Update update_feedback method to accept feedback_on:

    def update_feedback(self, feedback_index: int, feedback: str = None, 
                    feedback_on: str = None) -> Dict:
        """Update feedback entry"""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []
            
            if feedback is not None:
                updates.append("feedback = %s")
                params.append(feedback)
            
            if feedback_on is not None:
                updates.append("feedback_on = %s")
                params.append(feedback_on)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            # Always update edit_datetime
            updates.append("edit_datetime = NOW()")
            
            params.append(feedback_index)
            query = f"UPDATE feedback SET {', '.join(updates)} WHERE index = %s RETURNING *;"
            cursor.execute(query, params)
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            if result:
                return {
                    "success": True,
                    "message": "Feedback updated successfully",
                    "feedback_index": result[0],
                    "meeting_id": result[1],
                    "feedback": result[2],
                    "feedback_on": result[3],
                    "edit_datetime": result[4]
                }
            return {"success": False, "message": "Feedback not found"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error updating feedback: {e}"}

    def delete_feedback(self, feedback_index: int) -> Dict:
        """Delete a feedback entry"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM feedback WHERE index = %s RETURNING index;"
            cursor.execute(query, (feedback_index,))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            if result:
                return {"success": True, "message": "Feedback deleted successfully"}
            else:
                return {"success": False, "message": "Feedback not found"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting feedback: {e}"}
        
        
    # ==================== CONTENT VERSION OPERATIONS ====================
    def create_content_version(self, meeting_id: str, content_type: str, content: str, 
                              created_by: str = "SYSTEM") -> Dict[str, Any]:
        """
        Create a new content version (auto-increments version_number)
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content ('transcript', 'summary', 'recommendations', 'questions', 'notes')
            content: The actual content (with <del> tags for edits)
            created_by: advisor_id or 'SYSTEM'/'AI_PROCESSOR'
        
        Returns:
            Dict with success status and version details
        """
        try:
            cursor = self.conn.cursor()
            
            # Get next version number for this content type
            cursor.execute("""
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s;
            """, (meeting_id, content_type))
            next_version = cursor.fetchone()[0]
            
            # Set previous current version to false
            cursor.execute("""
                UPDATE meeting_content_versions
                SET is_current = FALSE
                WHERE meeting_id = %s AND content_type = %s AND is_current = TRUE;
            """, (meeting_id, content_type))
            
            # Insert new version
            cursor.execute("""
                INSERT INTO meeting_content_versions 
                (meeting_id, content_type, version_number, content, created_by, created_at, is_current)
                VALUES (%s, %s, %s, %s, %s, NOW(), TRUE)
                RETURNING version_id, version_number, created_at;
            """, (meeting_id, content_type, next_version, content, created_by))
            
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": f"{content_type.capitalize()} version {next_version} created",
                "version_id": result[0],
                "version_number": result[1],
                "created_at": result[2]
            }
            
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating version: {e}"}
    
    def get_content_version(self, meeting_id: str, content_type: str, 
                           version_number: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific content version
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content
            version_number: Version number to retrieve
        
        Returns:
            Version details or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT version_id, meeting_id, content_type, version_number, 
                       content, created_by, created_at, is_current
                FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s AND version_number = %s;
            """, (meeting_id, content_type, version_number))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "version_id": result[0],
                    "meeting_id": result[1],
                    "content_type": result[2],
                    "version_number": result[3],
                    "content": result[4],
                    "created_by": result[5],
                    "created_at": result[6],
                    "is_current": result[7]
                }
            return None
            
        except Error as e:
            print(f"Error fetching version: {e}")
            return None
    
    def list_content_versions(self, meeting_id: str, 
                             content_type: str = None) -> List[Dict[str, Any]]:
        """
        List all versions for a meeting (optionally filtered by content_type)
        
        Args:
            meeting_id: Meeting identifier
            content_type: Optional filter for specific content type
        
        Returns:
            List of versions (without full content, just metadata)
        """
        try:
            cursor = self.conn.cursor()
            
            if content_type:
                query = """
                    SELECT version_id, meeting_id, content_type, version_number,
                           created_by, created_at, is_current,
                           LENGTH(content) as content_length
                    FROM meeting_content_versions
                    WHERE meeting_id = %s AND content_type = %s
                    ORDER BY version_number DESC;
                """
                cursor.execute(query, (meeting_id, content_type))
            else:
                query = """
                    SELECT version_id, meeting_id, content_type, version_number,
                           created_by, created_at, is_current,
                           LENGTH(content) as content_length
                    FROM meeting_content_versions
                    WHERE meeting_id = %s
                    ORDER BY created_at DESC;
                """
                cursor.execute(query, (meeting_id,))
            
            results = cursor.fetchall()
            cursor.close()
            
            versions = []
            for row in results:
                versions.append({
                    "version_id": row[0],
                    "meeting_id": row[1],
                    "content_type": row[2],
                    "version_number": row[3],
                    "created_by": row[4],
                    "created_at": row[5],
                    "is_current": row[6],
                    "content_length": row[7]
                })
            
            return versions
            
        except Error as e:
            print(f"Error listing versions: {e}")
            return []
    
    def get_current_content_version(self, meeting_id: str, 
                                    content_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the current (active) version for a specific content type
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content
        
        Returns:
            Current version details or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT version_id, meeting_id, content_type, version_number,
                       content, created_by, created_at, is_current
                FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s AND is_current = TRUE;
            """, (meeting_id, content_type))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "version_id": result[0],
                    "meeting_id": result[1],
                    "content_type": result[2],
                    "version_number": result[3],
                    "content": result[4],
                    "created_by": result[5],
                    "created_at": result[6],
                    "is_current": result[7]
                }
            return None
            
        except Error as e:
            print(f"Error fetching current version: {e}")
            return None
    
    def set_current_content_version(self, meeting_id: str, content_type: str, 
                                   version_number: int) -> Dict[str, Any]:
        """
        Mark a specific version as current (used for rollback)
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content
            version_number: Version to make current
        
        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()
            
            # Verify version exists
            cursor.execute("""
                SELECT version_id FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s AND version_number = %s;
            """, (meeting_id, content_type, version_number))
            
            if not cursor.fetchone():
                cursor.close()
                return {"success": False, "message": "Version not found"}
            
            # Set all versions to not current
            cursor.execute("""
                UPDATE meeting_content_versions
                SET is_current = FALSE
                WHERE meeting_id = %s AND content_type = %s;
            """, (meeting_id, content_type))
            
            # Set target version to current
            cursor.execute("""
                UPDATE meeting_content_versions
                SET is_current = TRUE
                WHERE meeting_id = %s AND content_type = %s AND version_number = %s;
            """, (meeting_id, content_type, version_number))
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": f"Version {version_number} is now current"
            }
            
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error setting current version: {e}"}
    
    def rollback_content_to_version(self, meeting_id: str, content_type: str, 
                                   version_number: int) -> Dict[str, Any]:
        """
        Rollback content to a previous version (makes it current and updates meeting_details)
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content ('transcript' or 'summary')
            version_number: Version to rollback to
        
        Returns:
            Success status with content
        """
        try:
            cursor = self.conn.cursor()
            
            # Get the version content
            cursor.execute("""
                SELECT content FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s AND version_number = %s;
            """, (meeting_id, content_type, version_number))
            
            result = cursor.fetchone()
            if not result:
                cursor.close()
                return {"success": False, "message": "Version not found"}
            
            content = result[0]
            
            # Set this version as current
            cursor.execute("""
                UPDATE meeting_content_versions
                SET is_current = FALSE
                WHERE meeting_id = %s AND content_type = %s;
            """, (meeting_id, content_type))
            
            cursor.execute("""
                UPDATE meeting_content_versions
                SET is_current = TRUE
                WHERE meeting_id = %s AND content_type = %s AND version_number = %s;
            """, (meeting_id, content_type, version_number))
            
            # Update meeting_details table with this content
            if content_type == 'transcript':
                cursor.execute("""
                    UPDATE meeting_details
                    SET transcript = %s, updated_datetime = NOW()
                    WHERE meeting_id = %s;
                """, (content, meeting_id))
            elif content_type == 'summary':
                cursor.execute("""
                    UPDATE meeting_details
                    SET summary = %s, updated_datetime = NOW()
                    WHERE meeting_id = %s;
                """, (content, meeting_id))
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": f"Rolled back to version {version_number}",
                "content": content,
                "version_number": version_number
            }
            
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error rolling back: {e}"}
    
    def get_content_version_count(self, meeting_id: str, content_type: str) -> int:
        """
        Count total versions for a specific content type
        
        Args:
            meeting_id: Meeting identifier
            content_type: Type of content
        
        Returns:
            Number of versions
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM meeting_content_versions
                WHERE meeting_id = %s AND content_type = %s;
            """, (meeting_id, content_type))
            
            count = cursor.fetchone()[0]
            cursor.close()
            return count
            
        except Error as e:
            print(f"Error counting versions: {e}")
            return 0
    
    def get_unified_timeline(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get unified timeline of all edits across all content types
        
        Args:
            meeting_id: Meeting identifier
        
        Returns:
            List of all versions sorted chronologically
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT version_id, meeting_id, content_type, version_number,
                       created_by, created_at, is_current,
                       LENGTH(content) as content_length
                FROM meeting_content_versions
                WHERE meeting_id = %s
                ORDER BY created_at DESC;
            """, (meeting_id,))
            
            results = cursor.fetchall()
            cursor.close()
            
            timeline = []
            for row in results:
                timeline.append({
                    "version_id": row[0],
                    "meeting_id": row[1],
                    "content_type": row[2],
                    "version_number": row[3],
                    "created_by": row[4],
                    "created_at": row[5],
                    "is_current": row[6],
                    "content_length": row[7]
                })
            
            return timeline
            
        except Error as e:
            print(f"Error fetching timeline: {e}")
            return []
        

    # ==================== CHAT OPERATIONS ====================
    
    def create_chat(self, chat_id: str, meeting_id: str, user_id: str) -> Dict:
        """Create a new chat session for a meeting"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO chat (id, meeting_id, user_id, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING id, meeting_id, user_id, created_at;
            """
            cursor.execute(query, (chat_id, meeting_id, user_id))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": "Chat created successfully",
                "chat_id": result[0],
                "meeting_id": result[1],
                "user_id": result[2],
                "created_at": result[3]
            }
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating chat: {e}"}
    
    def get_chat(self, chat_id: str) -> Optional[Dict]:
        """Get chat by ID"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT id, meeting_id, user_id, created_at, updated_at, deleted_at FROM chat WHERE id = %s;"
            cursor.execute(query, (chat_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "chat_id": result[0],
                    "meeting_id": result[1],
                    "user_id": result[2],
                    "created_at": result[3],
                    "updated_at": result[4],
                    "deleted_at": result[5]
                }
            return None
        except Error as e:
            print(f"Error fetching chat: {e}")
            return None
    
    def get_active_chat_for_meeting(self, meeting_id: str) -> Optional[Dict]:
        """Get active (non-deleted) chat for a meeting"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT id, meeting_id, user_id, created_at, updated_at
                FROM chat
                WHERE meeting_id = %s AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1;
            """
            cursor.execute(query, (meeting_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "chat_id": result[0],
                    "meeting_id": result[1],
                    "user_id": result[2],
                    "created_at": result[3],
                    "updated_at": result[4]
                }
            return None
        except Error as e:
            print(f"Error fetching active chat: {e}")
            return None
    
    def soft_delete_chat(self, chat_id: str) -> Dict:
        """Soft delete a chat (set deleted_at timestamp)"""
        try:
            cursor = self.conn.cursor()
            query = """
                UPDATE chat
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id;
            """
            cursor.execute(query, (chat_id,))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            if result:
                return {"success": True, "message": "Chat soft deleted successfully"}
            else:
                return {"success": False, "message": "Chat not found or already deleted"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error soft deleting chat: {e}"}
    
    # ==================== MESSAGE OPERATIONS ====================
    
    def create_message(self, message_id: str, chat_id: str, content: str, sender_type: str) -> Dict:
        """Create a new message in a chat"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO message (id, chat_id, content, sender_type, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING id, chat_id, content, sender_type, created_at;
            """
            cursor.execute(query, (message_id, chat_id, content, sender_type))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "message": "Message created successfully",
                "message_id": result[0],
                "chat_id": result[1],
                "content": result[2],
                "sender_type": result[3],
                "created_at": result[4]
            }
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating message: {e}"}
    
    def get_chat_messages(self, chat_id: str, include_deleted: bool = False) -> List[Dict]:
        """Get all messages for a chat, ordered by creation time"""
        try:
            cursor = self.conn.cursor()
            
            if include_deleted:
                query = """
                    SELECT id, chat_id, content, sender_type, created_at, updated_at, deleted_at
                    FROM message
                    WHERE chat_id = %s
                    ORDER BY created_at ASC;
                """
            else:
                query = """
                    SELECT id, chat_id, content, sender_type, created_at, updated_at, deleted_at
                    FROM message
                    WHERE chat_id = %s AND deleted_at IS NULL
                    ORDER BY created_at ASC;
                """
            
            cursor.execute(query, (chat_id,))
            results = cursor.fetchall()
            cursor.close()
            
            messages = []
            for row in results:
                messages.append({
                    "message_id": row[0],
                    "chat_id": row[1],
                    "content": row[2],
                    "sender_type": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "deleted_at": row[6]
                })
            return messages
        except Error as e:
            print(f"Error fetching chat messages: {e}")
            return []

    # ==================== TRANSCRIPTION STATUS OPERATIONS ====================

    def insert_queued_transcription(self, blob_name: str, meeting_id: str, 
                                file_size_bytes: int) -> Dict:
        """
        Insert initial 'queued' status when audio is uploaded.
        Uses ON CONFLICT DO NOTHING to prevent duplicates.
        """
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO processed_audio_files 
                (blob_name, meeting_id, status, processed_datetime, file_size_bytes)
                VALUES (%s, %s, 'queued', NOW(), %s)
                ON CONFLICT (blob_name) DO NOTHING
                RETURNING blob_name;
            """
            cursor.execute(query, (blob_name, meeting_id, file_size_bytes))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            
            if result:
                return {"success": True, "message": "Audio queued for transcription"}
            else:
                return {"success": True, "message": "Audio already queued"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error queueing audio: {e}"}


    def check_meeting_transcription_status(self, meeting_id: str) -> Dict:
        """
        Check if all audio files for a meeting have finished processing.
        
        Returns:
            Dict with completion status and counts by status type
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT status, COUNT(*) as count
                FROM processed_audio_files
                WHERE meeting_id = %s
                GROUP BY status;
            """
            cursor.execute(query, (meeting_id,))
            results = cursor.fetchall()
            cursor.close()
            
            # Initialize counts
            status_counts = {
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
            
            total_files = 0
            for row in results:
                status = row[0]
                count = row[1]
                if status in status_counts:
                    status_counts[status] = count
                total_files += count
            
            # All completed if no files are queued or processing
            all_completed = (status_counts["queued"] + status_counts["processing"]) == 0
            
            return {
                "success": True,
                "all_completed": all_completed,
                "total_files": total_files,
                **status_counts
            }
            
        except Error as e:
            print(f"Error checking transcription status: {e}")
            return {
                "success": False,
                "message": f"Error checking status: {e}",
                "all_completed": False,
                "total_files": 0,
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }

    # ==================== QUESTION TEMPLATE OPERATIONS ====================

    def list_question_templates(self) -> List[Dict]:
        """List all question templates with type and question count"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT
                    t.template_id,
                    t.template_name,
                    t.template_owner,
                    t.template_type,
                    t.updated_at,
                    COUNT(q.question_id) AS question_count
                FROM question_template t
                LEFT JOIN question_section s ON s.template_id = t.template_id
                LEFT JOIN question q ON q.section_id = s.section_id
                GROUP BY t.template_id, t.template_name, t.template_owner, t.template_type, t.updated_at, t.created_at
                ORDER BY t.created_at;
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()

            templates = []
            for row in results:
                templates.append({
                    "template_id": row[0],
                    "template_name": row[1],
                    "template_owner": row[2],
                    "template_type": row[3],
                    "last_modified": row[4].isoformat() if row[4] else None,
                    "number_of_questions": row[5] or 0
                })
            return templates
        except Error as e:
            print(f"Error listing question templates: {e}")
            return []

    def delete_question_template(self, template_id: str) -> Dict:
        """Delete a question template (cascades to sections and questions)"""
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM question_template WHERE template_id = %s;"
            cursor.execute(query, (template_id,))
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Question template deleted successfully"}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error deleting question template: {e}"}


    # ==================== QUESTION SECTION OPERATIONS ====================

    def list_question_sections(self, template_id: str) -> List[Dict]:
        """List all sections for a given template, ordered by sort_order"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM question_section WHERE template_id = %s ORDER BY sort_order;"
            cursor.execute(query, (template_id,))
            results = cursor.fetchall()
            cursor.close()

            sections = []
            for row in results:
                sections.append({
                    "section_id": row[0],
                    "template_id": row[1],
                    "name": row[2],
                    "sort_order": row[3],
                    "created_at": row[4]
                })
            return sections
        except Error as e:
            print(f"Error listing question sections: {e}")
            return []

    def list_questions_by_section(self, section_id: str) -> List[Dict]:
        """List all questions for a given section, ordered by sort_order"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM question WHERE section_id = %s ORDER BY sort_order;"
            cursor.execute(query, (section_id,))
            results = cursor.fetchall()
            cursor.close()

            questions = []
            for row in results:
                questions.append({
                    "question_id": row[0],
                    "section_id": row[1],
                    "content": row[2],
                    "sort_order": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                })
            return questions
        except Error as e:
            print(f"Error listing questions: {e}")
            return []

    # ==================== DETAILED TEMPLATE OPERATIONS ====================


    # ==================== FULL TEMPLATE WITH QUESTIONS ====================

    def get_detailed_template(self, template_id: str) -> Optional[Dict]:
        """Get a complete template with all sections and questions (structured like TCP_QUESTIONS)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM question_template WHERE template_id = %s;", (template_id,))
            result = cursor.fetchone()
            cursor.close()

            if not result:
                return None

            template_type = result[3]
            template = {
                "template_id": result[0],
                "template_name": result[1],
                "template_owner": result[2],
                "template_type": template_type,
                "created_at": result[4].isoformat() if result[4] else None,
                "updated_at": result[5].isoformat() if result[5] else None
            }

            sections = self.list_question_sections(template_id)

            if template_type == "without-section":
                all_questions = []
                for section in sections:
                    questions = self.list_questions_by_section(section["section_id"])
                    all_questions.extend([q["content"] for q in questions])
                template["questions"] = all_questions
            else:
                sections_dict = {}
                for section in sections:
                    questions = self.list_questions_by_section(section["section_id"])
                    sections_dict[section["name"]] = [q["content"] for q in questions]
                template["questions"] = sections_dict

            return template
        except Error as e:
            print(f"Error fetching detailed template: {e}")
            return None

    def get_categorized_questions(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Returns data in the exact same format as CATEGORIZED_QUESTIONS from config/questions.py.

        Format: {template_name: {section_name: [question_strings]}}

        Uses template_name as the key (e.g. "Total Client Profile", "Pre Discovery").
        """
        try:
            result = {}
            templates = self.list_question_templates()

            for template in templates:
                template_name = template["template_name"]
                template_id = template["template_id"]

                sections = self.list_question_sections(template_id)
                sections_dict = {}
                for section in sections:
                    questions = self.list_questions_by_section(section["section_id"])
                    sections_dict[section["name"]] = [q["content"] for q in questions]

                result[template_name] = sections_dict

            return result
        except Error as e:
            print(f"Error fetching categorized questions: {e}")
            return {}

    def create_detailed_template(self, template_id: str, template_name: str, sections: Dict[str, List[str]], template_owner: str = None, template_type: str = "with-section") -> Dict:
        """
        Bulk create a template with all sections and questions in one go.

        Accepts the same format as TCP_QUESTIONS:
            sections = {"section 1 - values": ["question 1", "question 2"], ...}
        """
        try:
            import uuid
            cursor = self.conn.cursor()

            # Create template
            cursor.execute(
                "INSERT INTO question_template (template_id, template_name, template_owner, template_type, created_at, updated_at) VALUES (%s, %s, %s, %s, NOW(), NOW());",
                (template_id, template_name, template_owner, template_type)
            )

            # Create sections and questions (skip sections with no questions)
            for sort_order, (section_name, questions) in enumerate(sections.items()):
                if not questions:
                    continue
                section_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO question_section (section_id, template_id, name, sort_order, created_at) VALUES (%s, %s, %s, %s, NOW());",
                    (section_id, template_id, section_name, sort_order)
                )
                for q_order, content in enumerate(questions):
                    question_id = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO question (question_id, section_id, content, sort_order, created_at, updated_at) VALUES (%s, %s, %s, %s, NOW(), NOW());",
                        (question_id, section_id, content, q_order)
                    )

            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Template created successfully", "template_id": template_id}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating full template: {e}"}

    def save_detailed_template(self, template_id: str, template_name: str, sections: Dict[str, List[str]], template_owner: str = None, template_type: str = None) -> Dict:
        """
        Full replace of a template's sections and questions.
        Deletes all existing sections/questions and re-inserts from the payload.
        """
        try:
            import uuid
            cursor = self.conn.cursor()

            # Update template metadata
            if template_type:
                cursor.execute(
                    "UPDATE question_template SET template_name = %s, template_owner = %s, template_type = %s, updated_at = NOW() WHERE template_id = %s;",
                    (template_name, template_owner, template_type, template_id)
                )
            else:
                cursor.execute(
                    "UPDATE question_template SET template_name = %s, template_owner = %s, updated_at = NOW() WHERE template_id = %s;",
                    (template_name, template_owner, template_id)
                )
            if cursor.rowcount == 0:
                cursor.close()
                return {"success": False, "message": "Template not found"}

            # Delete old sections (cascades to questions)
            cursor.execute(
                "DELETE FROM question_section WHERE template_id = %s;",
                (template_id,)
            )

            # Insert new sections and questions (skip sections with no questions)
            for sort_order, (section_name, questions) in enumerate(sections.items()):
                if not questions:
                    continue
                section_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO question_section (section_id, template_id, name, sort_order, created_at) VALUES (%s, %s, %s, %s, NOW());",
                    (section_id, template_id, section_name, sort_order)
                )
                for q_order, content in enumerate(questions):
                    question_id = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO question (question_id, section_id, content, sort_order, created_at, updated_at) VALUES (%s, %s, %s, %s, NOW(), NOW());",
                        (question_id, section_id, content, q_order)
                    )

            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Template saved successfully", "template_id": template_id}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error saving template: {e}"}