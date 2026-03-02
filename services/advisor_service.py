from typing import Dict, List, Optional, Any
from utils.db_utils import DatabaseUtils


class AdvisorService:
    """Service layer for advisor-related operations.

    Methods accept an optional `conn` argument (psycopg2 connection) so callers
    can pass the shared `app.state.db_conn` or a per-request connection.
    """

    def create_advisor(self, advisor_id: str, name: str, email: str = None, 
                       role: str = "Advisor", conn=None) -> Dict[str, Any]:
        """Create a new advisor (simplified - no client_ids)"""
        db = DatabaseUtils(conn)
        return db.create_advisor(
            advisor_id=advisor_id, 
            name=name, 
            email=email, 
            role=role
        )

    def get_advisor_profile(self, advisor_id: str, conn=None) -> Dict[str, Any]:
        """Get advisor profile by ID"""
        db = DatabaseUtils(conn)
        advisor = db.get_advisor(advisor_id)
        if not advisor:
            return {"found": False, "message": "Advisor not found"}
        return {"found": True, "advisor": advisor}

    def update_advisor(self, advisor_id: str, name: str = None, email: str = None,
                       role: str = None, conn=None) -> Dict[str, Any]:
        """Update advisor details"""
        db = DatabaseUtils(conn)
        return db.update_advisor(
            advisor_id=advisor_id, 
            name=name, 
            email=email, 
            role=role
        )

    def delete_advisor(self, advisor_id: str, conn=None) -> Dict[str, Any]:
        """Delete an advisor"""
        db = DatabaseUtils(conn)
        return db.delete_advisor(advisor_id=advisor_id)

    def list_advisors(self, conn=None) -> List[Dict[str, Any]]:
        """List all advisors"""
        db = DatabaseUtils(conn)
        return db.list_advisors()

    def get_advisor_clients(self, advisor_id: str, page: int = 1, rows_per_page: int = 10, client_name: str = None, conn=None) -> Dict[str, Any]:
        """Get clients for an advisor with pagination and optional name filter"""
        db = DatabaseUtils(conn)
        return db.list_clients_paginated(advisor_id=advisor_id, page=page, rows_per_page=rows_per_page, client_name=client_name)

    def get_advisor_meetings(
        self, 
        advisor_id: str,
        search: str = None,
        meeting_types: List[str] = None,
        date_from: str = None,
        date_to: str = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 10,
        conn=None
    ) -> Dict[str, Any]:
        """
        Get paginated meetings for an advisor with search, filtering, and sorting
        
        Args:
            advisor_id: The advisor ID
            search: Search term for client name, meeting name, or meeting type
            meeting_types: List of meeting types to filter
            date_from: Start date filter (ISO format)
            date_to: End date filter (ISO format)
            sort_by: Field to sort by ('date' or 'client_name')
            sort_order: Sort order ('asc' or 'desc')
            page: Page number (1-indexed)
            per_page: Records per page
            conn: Database connection
        
        Returns:
            Dict with meetings data and pagination metadata
        """
        db = DatabaseUtils(conn)
        
        result = db.list_meetings_paginated(
            advisor_id=advisor_id,
            search=search,
            meeting_types=meeting_types,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        return result

    def get_advisor_statistics(self, advisor_id: str, conn=None) -> Dict[str, Any]:
        """Get statistics for an advisor (clients, meetings, etc.)"""
        db = DatabaseUtils(conn)
        
        # Get clients
        clients = db.list_clients(advisor_id=advisor_id)
        
        # Get meetings
        meetings = db.list_meetings(advisor_id=advisor_id)
        
        # Count meeting statuses
        meeting_status_counts = {}
        for meeting in meetings:
            status = meeting.get("status", "Unknown")
            meeting_status_counts[status] = meeting_status_counts.get(status, 0) + 1
        
        # Count client statuses
        client_status_counts = {}
        for client in clients:
            status = client.get("status", "Unknown")
            client_status_counts[status] = client_status_counts.get(status, 0) + 1
        
        return {
            "advisor_id": advisor_id,
            "total_clients": len(clients),
            "total_meetings": len(meetings),
            "client_status_breakdown": client_status_counts,
            "meeting_status_breakdown": meeting_status_counts
        }
    

    def get_advisor_by_email(self, email: str, conn=None) -> Optional[Dict[str, Any]]:
        """Get advisor by email address"""
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM advisors WHERE email = %s LIMIT 1;"
            cursor.execute(query, (email,))
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
        except Exception as e:
            print(f"Error fetching advisor by email: {e}")
            return None


    def get_or_create_user_from_token(self, oid: str, email: str, name: str, conn=None) -> Optional[Dict[str, Any]]:
        """
        Get existing user or create new advisor from validated token
        
        Args:
            oid: Microsoft user object ID
            email: User email from token
            name: User display name from token
            conn: Database connection
        
        Returns:
            User/advisor record
        """
        db = DatabaseUtils(conn)
        
        # Try to find by OID (advisor_id)
        user = db.get_advisor(oid)
        
        if user:
            # Update email/name if changed
            if user.get("email") != email or user.get("name") != name:
                db.update_advisor(advisor_id=oid, name=name, email=email)
                user = db.get_advisor(oid)
            return user
        
        # Check if email exists with different advisor_id
        existing_by_email = self.get_advisor_by_email(email, conn)
        
        if existing_by_email and existing_by_email.get("advisor_id") != oid:
            # Email exists but with old ID - update to use OID
            old_id = existing_by_email["advisor_id"]
            db.delete_advisor(old_id)
            db.create_advisor(
                advisor_id=oid,
                name=name,
                email=email,
                role=existing_by_email.get("role", "Advisor")
            )
            return db.get_advisor(oid)
        
        # User doesn't exist - create new
        result = db.create_advisor(
            advisor_id=oid,
            name=name,
            email=email,
            role="Advisor"
        )
        
        if result.get("success"):
            return db.get_advisor(oid)
        
        return None