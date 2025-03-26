from fastapi import FastAPI, HTTPException,APIRouter
from Application.endpoints.guest_user_endpoint import guest_router
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[""], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guest_router, prefix="/Guest_user", tags=["Guest_user"])

#uvicorn Application.endpoints.app:app 
