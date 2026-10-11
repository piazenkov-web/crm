"""Contract-only FastAPI transport. Every adapter stays disabled.
Static service token is a local harness choice; production requires authenticated
service identities and server-side sessions with object-level authorization.
"""
import os, secrets
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import FastAPI, Body, Header, HTTPException
from jsonschema import ValidationError
from .contracts import TOOLS, validate_input, validate_output
app=FastAPI(title='IA v4 contract harness — adapters disabled',version='4.0')
@app.get('/health')
def health():
    return {'status':'contract_harness','adapters_enabled':False,'tool_count':len(TOOLS)}
@app.post('/internal/v4/tools/{name}')
def tool_contract(name:str,payload:dict=Body(...),authorization:str|None=Header(None),idempotency_key:str|None=Header(None),x_confirmation_id:str|None=Header(None)):
    token=os.getenv('HARNESS_SERVICE_TOKEN')
    if not token or len(token)<32:
        raise HTTPException(503,'Harness token not configured')
    if not authorization or not secrets.compare_digest(authorization,'Bearer '+token):
        raise HTTPException(401,'Service authentication required')
    t=TOOLS.get(name)
    if t is None:raise HTTPException(404,'Unknown tool')
    try:validate_input(name,payload)
    except ValidationError:raise HTTPException(422,'Arguments do not match schema')
    if t['mode']!='READ' and (not idempotency_key or not 16<=len(idempotency_key)<=128):
        raise HTTPException(422,'Idempotency-Key required')
    # A header is not proof of confirmation. No real action is attempted by harness.
    result={'ok':False,'request_id':str(uuid4()),'error':{'code':'CAPABILITY_DISABLED','message':'Adapter is not implemented. This harness cannot perform real actions.','retryable':False,'operation_id':None}}
    validate_output(name,result)
    return result
