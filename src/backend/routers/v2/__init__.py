from fastapi import APIRouter

from . import citation, dashboard, facts, mfs, query, search, vic_afs, vic_bpo

router = APIRouter(prefix="/v2", tags=["v2"])
router.include_router(citation.router)
router.include_router(facts.router)
router.include_router(query.router)
router.include_router(dashboard.router)
router.include_router(search.router)
router.include_router(mfs.router)
router.include_router(vic_afs.router)
router.include_router(vic_bpo.router)
