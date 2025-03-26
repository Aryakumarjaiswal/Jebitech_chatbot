from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from Application.database import get_db, Session_Table, Chat
from Application.endpoints.search_reference_id import find_reference_id
from Application.endpoints.prompt_generator import guest_prompt
from Application.sql_response import execute_sql,get_property_names,clean_user_input,final_answer,property_name_identifier
import pymysql
import uuid
import os
import re



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("guest_user.log", mode="a"), logging.StreamHandler()],
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY environment variable is missing!")
    raise ValueError("GEMINI_KEY is not set in environment variables")

genai.configure(api_key=GEMINI_API_KEY)


guest_router = APIRouter()

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

import re

def extract_user_id(text: str) -> str:
    """
    Extracts a user ID from a given text.
    """
    pattern = r"\b(?:[0-9a-f]{24}|\d{8})\b"
    match = re.search(pattern, text, re.IGNORECASE)

    return match.group(0) if match else "None"

model2 = genai.GenerativeModel(
    model_name= "gemini-2.0-flash",  
    generation_config=generation_config,
    system_instruction=guest_prompt,
    tools=[extract_user_id]
)
chat_session = model2.start_chat()
session_id = None
user_id = None

def ensure_guest_session(db: Session):
    global session_id, user_id
    
    if session_id is None:
        user_id = str(uuid.uuid4())  
        session_id = str(uuid.uuid4())  
        
        new_session = Session_Table(
            session_id=session_id,
            user_id=user_id,
            user_type="guest",
            status="active",
            started_at=datetime.utcnow(),
        )
        
        db.add(new_session)
        db.commit()
        
        
        print(f"New guest session created - Session ID: {session_id}, User ID: {user_id}")
    
    return session_id, user_id



    


@guest_router.post("/chat/guest")
def chat_with_bot( user_input: str, db: Session = Depends(get_db)):
    """Takes user input, generates LLM response, and appends conversation in DB."""


    session_id, user_id = ensure_guest_session(db)
    user = db.query(Session_Table).filter_by(session_id=session_id).first()
    record_search = db.query(Chat).filter_by(session_id=session_id).first()
    flag=0
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid session ID")
        
        
    property_list=list(get_property_names())
    #print(property_list)
 
    result = property_name_identifier(user_input, property_list)

    if result not in [None, "No matching property found."]:  
        property_name= result  
        #print("Retrieve property name:",property_name)  
    else:
        property_name="No matching property found."
    #print("User Input: ",user_input,"Retrieved property name: ",property_name)

    modified_input = f"User asked:{user_input},property_name:{property_name}"     
    #print(modified_input)
    response = chat_session.send_message(modified_input)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "function_call") and part.function_call is not None and part.function_call.name == "extract_user_id":
            id = extract_user_id(user_input)
            #print(id)
            if id != None:
                referenced_property=find_reference_id(id)
                if referenced_property !=0 and referenced_property!=-1:
                    generated_sql = f"select summary from property_data_live where nick_name = '{referenced_property}' or property_building = '{referenced_property}' or property_id = '{referenced_property}';"
  
                    flag=1
               

                    query_result = execute_sql(generated_sql)
                    #print(query_result)
                    new_input=f"User asked:{user_input}. The query result is: {query_result}.(He is verified user) Format it for user understanding in natural language professionaly."
           
                    final_response=final_answer(new_input)
         
                    generated_sql = final_response
                if referenced_property==0:
                     generated_sql="Reservation ID provided by you is expired thus no property is associated with you"
                if referenced_property==-1:
                     generated_sql="Invalid Reservation ID is provided kindly double check your Reservation ID !!!"
                user.ended_at = datetime.utcnow()
                message_container=f"\n USER-> {user_input}\n RESPONSE-> {generated_sql}"
                
                if not record_search:
                    first_chat = Chat(
            session_id=session_id,
            sender="user",
            message=message_container,
            sent_at=datetime.utcnow(),
            status="read"
        )
                    
                    
                    db.add(first_chat)
                    
                if user.started_at:
                    user.Duration = (user.ended_at - user.started_at).total_seconds() 
                
                    record_search.message = str((record_search.message or "") + message_container)
                    record_search.sent_at = datetime.utcnow()

            
                db.commit()
                db.refresh(user)
                db.refresh(record_search)

                return {"session_id": session_id,
            "User: ":user_input,
            "AI Response: ":generated_sql}

            if id==None:
                 final_string="Please enter valid Reference ID as no User found with this ID"
            
            user.ended_at = datetime.utcnow()
            message_container=f"\n USER-> {user_input}\n RESPONSE->{final_string}."
                
            if not record_search:
                        

                        first_chat = Chat(
            session_id=session_id,
            sender="user",
            message=message_container,
            sent_at=datetime.utcnow(),
            status="read"
        )
                    
                    
                        db.add(first_chat)
                    
            if user.started_at:
                    user.Duration = (user.ended_at - user.started_at).total_seconds() 
                
                    record_search.message = str((record_search.message or "") + message_container)
                    record_search.sent_at = datetime.utcnow()

                
            db.commit()
            db.refresh(user)
            db.refresh(record_search)
            return {"session_id": session_id,
             "User: ":user_input,
             "AI Response: ":"Please enter valid Reference ID as no user found with this ID."}


    generated_sql = response.text

    if  flag==0 and "property_data_live" in generated_sql : 


        logging.info("SQL query detected in response")
        
        query_result = execute_sql(generated_sql)
        #print(generated_sql)
        final_response = chat_session.send_message(
            f"User asked: '{user_input}'. The query result is: {query_result}.(He is not verified user thus NEVER provide any sensitive information if{user_input} contains.) Format it for user understanding in natural language professionaly but if they seek any information from (Not allowed )field then professionally say no to user.Also answer only  what is asked please.No Unecessary information."
        )
        response_text = final_response.candidates[0].content.parts[0].text
        generated_sql=response_text

    
    else:
        logging.info("Non-SQL response detected")
        

    
    user.ended_at = datetime.utcnow()
    message_container=f"\n USER-> {user_input}\n RESPONSE-> {generated_sql}"
    if user.started_at:
        user.Duration = (user.ended_at - user.started_at).total_seconds() 
    if not record_search:
        first_chat = Chat(
            session_id=session_id,
            sender="user",
            message=message_container,
            sent_at=datetime.utcnow(),
            status="read"
        )
        db.add(first_chat)
    else:
        record_search.message = str((record_search.message or "") + message_container)
        record_search.sent_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"session_id": session_id,
             "User: ":user_input,
             "AI Response: ":generated_sql}



@guest_router.get("/Get_session_chat/")
def get_session_chat(session_id: str, db: Session = Depends(get_db)):
    """Fetches Conversation History for a given session ID."""
    
    record_search =db.query(Chat).filter_by(session_id = session_id).all() 

    if not record_search:
        raise HTTPException(status_code=400, detail="Please enter a valid session ID")

    messages = [record.message for record in record_search]  # Extract messages

    return {
        "Session ID": session_id,
        "Conversation History": messages
    }










