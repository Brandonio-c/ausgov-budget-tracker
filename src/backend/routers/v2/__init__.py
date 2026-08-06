from fastapi import APIRouter

from . import (
    citation,
    dashboard,
    facts,
    mfs,
    query,
    search,
    tas_ggs,
    vic_afs,
    vic_bpo,
    vic_bpo_soce_admin,
)

router = APIRouter(prefix="/v2", tags=["v2"])
router.include_router(citation.router)
router.include_router(facts.router)
router.include_router(query.router)
router.include_router(dashboard.router)
router.include_router(search.router)
router.include_router(mfs.router)
router.include_router(vic_afs.router)
router.include_router(vic_bpo.router)
router.include_router(vic_bpo_soce_admin.router)
router.include_router(tas_ggs.router)
