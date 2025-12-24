from typing import List, Dict, Any, Optional
from datetime import date
from decimal import Decimal
import json

from utils.db_utils import DatabaseUtils


class ClientService:
    """Service layer for client-related operations"""
    
    def __init__(self):
        pass

    def create_client_profile(self, client_id: str, name: str, advisor_id: str, 
                             status: str = "Active", conn=None) -> Dict[str, Any]:
        """Create a new client profile (simplified)"""
        db = DatabaseUtils(conn)
        
        client_created = db.create_client(
            client_id=client_id,
            name=name,
            advisor_id=advisor_id,
            status=status
        )
        
        if client_created["success"]:
            return {
                "success": True,
                "message": "Client profile created successfully",
                "client_id": client_id,
                "name": name,
                "advisor_id": advisor_id
            }
        else:
            return {
                "success": False,
                "message": f"Failed to create client: {client_created.get('message')}"
            }

    def get_client_profile(self, client_id: str, conn=None) -> Dict[str, Any]:
        """Fetch client profile with basic information"""
        db = DatabaseUtils(conn)
        client = db.get_client(client_id)
        
        if not client:
            return {
                "success": False,
                "message": "Client not found"
            }
        
        return {
            "success": True,
            "client_id": client["client_id"],
            "name": client["name"],
            "advisor_id": client["advisor_id"],
            "current_recommendation": client.get("current_recommendation"),
            "status": client.get("status"),
            "date_created": client.get("date_created")
        }

    def update_client_profile(self, client_id: str, updates: Dict[str, Any] = None, 
                             conn=None) -> Dict[str, Any]:
        """Update client profile with provided fields"""
        if not updates:
            return {
                "success": False,
                "message": "No updates provided"
            }
        
        db = DatabaseUtils(conn)
        
        # Extract valid fields for client table
        name = updates.get("name")
        advisor_id = updates.get("advisor_id")
        current_recommendation = updates.get("current_recommendation")
        status = updates.get("status")
        
        result = db.update_client(
            client_id=client_id,
            name=name,
            advisor_id=advisor_id,
            current_recommendation=current_recommendation,
            status=status
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Client profile updated successfully",
                "updates": updates
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update client: {result.get('message')}"
            }

    def get_client_meeting_history(self, client_id: str, conn=None) -> Dict[str, Any]:
        """Get all meetings for a client with details"""
        db = DatabaseUtils(conn)
        
        # Get all meetings for this client
        meetings = db.list_meetings(client_id=client_id)
        
        if not meetings:
            return {
                "success": True,
                "client_id": client_id,
                "total_meetings": 0,
                "meetings": []
            }
        
        # Enrich with meeting details
        meeting_list = []
        for meeting in meetings:
            meeting_id = meeting["meeting_id"]
            
            # Get meeting details
            details = db.get_meeting_detail(meeting_id)
            
            meeting_info = {
                "meeting_id": meeting_id,
                "meeting_type": meeting.get("meeting_type"),
                "status": meeting.get("status"),
                "created_datetime": meeting.get("created_datetime"),
                "advisor_id": meeting.get("advisor_id")
            }
            
            # Add details if available
            if details:
                meeting_info.update({
                    "summary": details.get("summary"),
                    "recommendations": details.get("recommendations"),
                    "advisor_notes": details.get("advisor_notes"),
                    "updated_datetime": details.get("updated_datetime")
                })
            
            meeting_list.append(meeting_info)
        
        return {
            "success": True,
            "client_id": client_id,
            "total_meetings": len(meeting_list),
            "meetings": meeting_list
        }

    def get_client_recommendation(self, client_id: str, conn=None) -> Dict[str, Any]:
        """Get current recommendation and historical recommendations from meetings"""
        db = DatabaseUtils(conn)
        
        # Get client's current recommendation
        client = db.get_client(client_id)
        if not client:
            return {
                "success": False,
                "message": "Client not found"
            }
        
        current_recommendation = client.get("current_recommendation")
        
        # Get recommendations from all meetings
        meetings = db.list_meetings(client_id=client_id)
        
        recommendations_history = []
        for meeting in meetings:
            meeting_id = meeting["meeting_id"]
            details = db.get_meeting_detail(meeting_id)
            
            if details and details.get("recommendations"):
                rec_raw = details.get("recommendations")
                
                # Try to parse if it's JSON
                try:
                    rec_val = json.loads(rec_raw) if isinstance(rec_raw, str) else rec_raw
                except Exception:
                    rec_val = rec_raw
                
                recommendations_history.append({
                    "meeting_id": meeting_id,
                    "meeting_type": meeting.get("meeting_type"),
                    "created_datetime": meeting.get("created_datetime"),
                    "recommendations": rec_val
                })
        
        return {
            "success": True,
            "client_id": client_id,
            "current_recommendation": current_recommendation,
            "recommendations_history": recommendations_history
        }

    # ==================== PRODUCT-RELATED OPERATIONS ====================
    
    def add_product_to_client(self, client_id: str, product_id: str, 
                             purchase_date: date = None, status: str = "Active",
                             investment_amount: Decimal = None, conn=None) -> Dict[str, Any]:
        """Add a product to a client's portfolio"""
        db = DatabaseUtils(conn)
        
        result = db.add_product_to_client(
            client_id=client_id,
            product_id=product_id,
            purchase_date=purchase_date,
            status=status,
            investment_amount=investment_amount
        )
        
        return result

    def remove_product_from_client(self, client_id: str, product_id: str, 
                                  conn=None) -> Dict[str, Any]:
        """Remove a product from a client's portfolio"""
        db = DatabaseUtils(conn)
        return db.remove_product_from_client(client_id=client_id, product_id=product_id)

    def get_client_products(self, client_id: str, conn=None) -> Dict[str, Any]:
        """Get all products for a client"""
        db = DatabaseUtils(conn)
        products = db.get_client_products(client_id)
        
        return {
            "success": True,
            "client_id": client_id,
            "total_products": len(products),
            "products": products
        }

    def get_client_portfolio_value(self, client_id: str, conn=None) -> Dict[str, Any]:
        """Calculate total portfolio value for a client"""
        db = DatabaseUtils(conn)
        products = db.get_client_products(client_id)
        
        total_value = Decimal("0.00")
        active_count = 0
        
        for product in products:
            if product.get("status") == "Active" and product.get("investment_amount"):
                total_value += Decimal(str(product["investment_amount"]))
                active_count += 1
        
        return {
            "success": True,
            "client_id": client_id,
            "total_portfolio_value": float(total_value),
            "active_products": active_count,
            "total_products": len(products)
        }