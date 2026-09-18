"""
REST API endpoints for incident data.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.integrations.data_store import DataStore
from app.models import Incident, ServiceHealth

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=List[Incident])
async def list_incidents(
    status: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    priority: Optional[str] = Query(None)
):
    store = DataStore.get_instance()
    return store.list_incidents(status=status, service=service, priority=priority)


@router.get("/active", response_model=List[Incident])
async def list_active_incidents(service: Optional[str] = Query(None)):
    store = DataStore.get_instance()
    active_statuses = ["in progress", "active", "open", "monitoring"]
    incidents = store.list_incidents()
    results = [i for i in incidents if i.status.lower() in active_statuses]
    if service:
        results = [i for i in results if service.lower() in i.service.lower()]
    return results


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    store = DataStore.get_instance()
    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@router.get("/services/health", response_model=List[ServiceHealth])
async def get_all_service_health():
    store = DataStore.get_instance()
    return store.get_all_services_status()


@router.get("/services/{service_name}/health", response_model=ServiceHealth)
async def get_service_health(service_name: str):
    store = DataStore.get_instance()
    service = store.get_service_health(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    return service
