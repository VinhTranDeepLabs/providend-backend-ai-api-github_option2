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

    def get_advisor_clients(self, advisor_id: str, conn=None) -> Dict[str, Any]:
        """Get all clients for an advisor (via FK relationship)"""
        db = DatabaseUtils(conn)
        clients = db.list_clients(advisor_id=advisor_id)
        
        # Format response
        clients_list = []
        for client in clients:
            clients_list.append({
                "client_id": client["client_id"],
                "name": client["name"],
                "status": client.get("status"),
                "current_recommendation": client.get("current_recommendation"),
                "date_created": client.get("date_created")
            })
        
        return {
            "advisor_id": advisor_id,
            "total_clients": len(clients_list),
            "clients": clients_list
        }

    def get_advisor_meetings(self, advisor_id: str, conn=None) -> Dict[str, Any]:
        """Get all meetings for an advisor with client and meeting details"""
        db = DatabaseUtils(conn)
        
        # Get all meetings for this advisor
        meetings = db.list_meetings(advisor_id=advisor_id)
        
        result = []
        for meeting in meetings:
            meeting_id = meeting["meeting_id"]
            client_id = meeting["client_id"]
            
            # Get client name
            client = db.get_client(client_id)
            client_name = client["name"] if client else "Unknown"
            
            # Get meeting details if available
            meeting_details = db.get_meeting_detail(meeting_id)
            
            result.append({
                "meeting_id": meeting_id,
                "client_id": client_id,
                "client_name": client_name,
                "meeting_type": meeting["meeting_type"],
                "status": meeting["status"],
                "created_datetime": meeting["created_datetime"],
                "has_details": meeting_details is not None,
                "summary": meeting_details.get("summary") if meeting_details else None
            })
        
        return {
            "advisor_id": advisor_id,
            "total_meetings": len(result),
            "meetings": result
        }

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