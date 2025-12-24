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
                      meeting_type: str = None, status: str = "Started") -> Dict:
        """Create a new meeting"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO meetings (meeting_id, client_id, advisor_id, meeting_type, created_datetime, status)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, client_id, advisor_id, meeting_type, status))
            result = cursor.fetchone()
            self.conn.commit()
            cursor.close()
            return {"success": True, "message": "Meeting created successfully", "meeting_id": result[0]}
        except Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error creating meeting: {e}"}
    
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
                    "status": result[5]
                }
            return None
        except Error as e:
            print(f"Error fetching meeting: {e}")
            return None
    
    def update_meeting(self, meeting_id: str, client_id: str = None, advisor_id: str = None,
                      meeting_type: str = None, status: str = None) -> Dict:
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
                    "status": row[5]
                })
            return meetings
        except Error as e:
            print(f"Error listing meetings: {e}")
            return []
    
    # ==================== MEETING DETAILS OPERATIONS ====================
    
    def create_meeting_detail(self, meeting_id: str, transcript: str = None, summary: str = None,
                             recommendations: str = None, questions: str = None, 
                             advisor_notes: str = None) -> Dict:
        """Create meeting details"""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO meeting_details (meeting_id, transcript, summary, recommendations, questions, advisor_notes, updated_datetime)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING *;
            """
            cursor.execute(query, (meeting_id, transcript, summary, recommendations, questions, advisor_notes))
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
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    "meeting_id": result[0],
                    "transcript": result[1],
                    "summary": result[2],
                    "recommendations": result[3],
                    "questions": result[4],
                    "advisor_notes": result[5],
                    "updated_datetime": result[6]
                }
            return None
        except Error as e:
            print(f"Error fetching meeting details: {e}")
            return None
    
    def update_meeting_detail(self, meeting_id: str, transcript: str = None, summary: str = None,
                             recommendations: str = None, questions: str = None,
                             advisor_notes: str = None) -> Dict:
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
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            # Always update the updated_datetime
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
            for row in results:
                details.append({
                    "meeting_id": row[0],
                    "transcript": row[1],
                    "summary": row[2],
                    "recommendations": row[3],
                    "questions": row[4],
                    "advisor_notes": row[5],
                    "updated_datetime": row[6]
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
        Combine all transcript segments into a single string.
        
        Args:
            meeting_id: The meeting ID
            separator: String to join segments (default: newline)
        
        Returns:
            Aggregated transcript string or None
        """
        segments = self.get_transcript_segments(meeting_id)
        
        if not segments:
            return None
        
        # Join all transcript texts
        full_transcript = separator.join([seg["transcript"] for seg in segments])
        return full_transcript
    
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