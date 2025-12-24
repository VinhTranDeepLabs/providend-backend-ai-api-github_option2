from fastapi import APIRouter, Request, Depends, Response, HTTPException
from fastapi import status as http_status
from typing import Optional
from datetime import date
from decimal import Decimal
from services.client_service import ClientService

router = APIRouter()
client_service = ClientService()


def get_conn(request: Request):
    """Return shared DB connection from app.state.db_conn."""
    conn = getattr(request.app.state, "db_conn", None)
    if conn is None:
        raise RuntimeError("DB connection not available on app.state.db_conn")
    return conn


@router.post("/create")
async def create_client_profile(
    client_id: str,
    name: str,
    advisor_id: str,
    client_status: str = "Active",
    conn=Depends(get_conn)
):
    """
    Create a new client profile.
    
    Args:
        client_id: Unique client identifier
        name: Full name of the client
        advisor_id: ID of the assigned advisor
        client_status: Client status (default: "Active")
    
    Returns:
        Created client details
    """
    result = client_service.create_client_profile(
        client_id=client_id,
        name=name,
        advisor_id=advisor_id,
        status=client_status,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to create client")
        )
    
    return result


@router.get("/{client_id}")
async def get_client_profile(client_id: str, conn=Depends(get_conn)):
    """
    Fetch client profile.
    
    Args:
        client_id: The client ID
    
    Returns:
        Client profile information
    """
    result = client_service.get_client_profile(client_id, conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return result


@router.patch("/{client_id}")
async def update_client_profile(
    client_id: str,
    name: Optional[str] = None,
    advisor_id: Optional[str] = None,
    current_recommendation: Optional[str] = None,
    client_status: Optional[str] = None,
    conn=Depends(get_conn)
):
    """
    Update client profile.
    
    Args:
        client_id: The client ID
        name: New name (optional)
        advisor_id: New advisor ID (optional)
        current_recommendation: New recommendation (optional)
        client_status: New status (optional)
    
    Returns:
        Update confirmation
    """
    updates = {}
    if name:
        updates["name"] = name
    if advisor_id:
        updates["advisor_id"] = advisor_id
    if current_recommendation is not None:
        updates["current_recommendation"] = current_recommendation
    if client_status:
        updates["status"] = client_status
    
    if not updates:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    result = client_service.update_client_profile(client_id, updates, conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to update client")
        )
    
    return result


@router.get("/{client_id}/meetings")
async def get_client_meeting_history(client_id: str, conn=Depends(get_conn)):
    """
    Get client meeting history.
    
    Args:
        client_id: The client ID
    
    Returns:
        List of all meetings for this client
    """
    result = client_service.get_client_meeting_history(client_id, conn)
    
    return result


@router.get("/{client_id}/recommendations")
async def get_client_recommendation(client_id: str, conn=Depends(get_conn)):
    """
    Get client recommendations (current + historical from meetings).
    
    Args:
        client_id: The client ID
    
    Returns:
        Current recommendation and historical recommendations from meetings
    """
    result = client_service.get_client_recommendation(client_id, conn)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "Client not found")
        )
    
    return result


# ==================== PRODUCT MANAGEMENT ENDPOINTS ====================

@router.get("/{client_id}/products")
async def get_client_products(client_id: str, conn=Depends(get_conn)):
    """
    Get all products for a client.
    
    Args:
        client_id: The client ID
    
    Returns:
        List of products in client's portfolio
    """
    result = client_service.get_client_products(client_id, conn)
    
    return result


@router.post("/{client_id}/products/{product_id}")
async def add_product_to_client(
    client_id: str,
    product_id: str,
    purchase_date: Optional[date] = None,
    product_status: str = "Active",
    investment_amount: Optional[float] = None,
    conn=Depends(get_conn)
):
    """
    Add a product to client's portfolio.
    
    Args:
        client_id: The client ID
        product_id: The product ID to add
        purchase_date: Date of purchase (optional)
        product_status: Product status (default: "Active")
        investment_amount: Investment amount (optional)
    
    Returns:
        Confirmation of product addition
    """
    # Convert float to Decimal if provided
    amount = Decimal(str(investment_amount)) if investment_amount else None
    
    result = client_service.add_product_to_client(
        client_id=client_id,
        product_id=product_id,
        purchase_date=purchase_date,
        status=product_status,
        investment_amount=amount,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to add product to client")
        )
    
    return {
        "success": True,
        "message": "Product added to client successfully",
        "client_id": client_id,
        "product_id": product_id
    }


@router.delete("/{client_id}/products/{product_id}")
async def remove_product_from_client(
    client_id: str,
    product_id: str,
    conn=Depends(get_conn)
):
    """
    Remove a product from client's portfolio.
    
    Args:
        client_id: The client ID
        product_id: The product ID to remove
    
    Returns:
        Confirmation of product removal
    """
    result = client_service.remove_product_from_client(
        client_id=client_id,
        product_id=product_id,
        conn=conn
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to remove product from client")
        )
    
    return {
        "success": True,
        "message": "Product removed from client successfully",
        "client_id": client_id,
        "product_id": product_id
    }


@router.get("/{client_id}/portfolio-value")
async def get_client_portfolio_value(client_id: str, conn=Depends(get_conn)):
    """
    Get total portfolio value for a client.
    
    Args:
        client_id: The client ID
    
    Returns:
        Total portfolio value and product counts
    """
    result = client_service.get_client_portfolio_value(client_id, conn)
    
    return result