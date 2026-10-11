import unittest, json
from uuid import uuid4
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from fastapi.testclient import TestClient
from app.contracts import ROOT, TOOLS, validate_input, validate_output
from app.main import app
import os
class Contracts(unittest.TestCase):
 def test_all_schemas_well_formed(self):
  for t in TOOLS.values():
   for k in ('input_schema','output_schema'):
    Draft202012Validator.check_schema(t[k])
  for n in ('events.schema.json','realtycalendar_webhook.schema.json','trusted_context.schema.json'):
   Draft202012Validator.check_schema(json.loads((ROOT/'contracts'/n).read_text()))
 def test_all_error_envelopes_valid(self):
  result={'ok':False,'request_id':str(uuid4()),'error':{'code':'CAPABILITY_DISABLED','message':'Disabled','retryable':False,'operation_id':None}}
  for name in TOOLS:validate_output(name,result)
 def test_reject_extra_tenant_in_model_payload(self):
  with self.assertRaises(ValidationError):validate_input('get_guest_profile',{'guest_id':str(uuid4()),'tenant_id':str(uuid4())})
 def test_uuid_enforced(self):
  with self.assertRaises(ValidationError):validate_input('get_booking',{'booking_id':'123'})
 def test_money_no_float(self):
  with self.assertRaises(ValidationError):validate_input('request_refund',{'booking_id':str(uuid4()),'refund_preview_id':str(uuid4()),'amount':{'amount_minor':12.5,'currency':'RUB'},'reason':'refund'})
 def test_invalid_date(self):
  with self.assertRaises(ValidationError):validate_input('check_availability',{'apartment_id':str(uuid4()),'check_in':'2026-02-30','check_out':'2026-03-04'})
 def test_fake_success_rejected(self):
  with self.assertRaises(ValidationError):validate_output('create_booking',{'ok':True,'request_id':str(uuid4()),'data':{'status':'CONFIRMED'},'source':'llm','observed_at':'2026-10-04T00:00:00Z'})
 def test_harness_never_reports_booking_success(self):
  os.environ['HARNESS_SERVICE_TOKEN']='a'*40
  c=TestClient(app)
  p={'guest_id':str(uuid4()),'quote_id':str(uuid4()),'inventory_version':'v1'}
  h={'Authorization':'Bearer '+'a'*40,'Idempotency-Key':'logical_operation_001'}
  r=c.post('/internal/v4/tools/create_booking',json=p,headers=h)
  self.assertEqual(r.status_code,200);self.assertFalse(r.json()['ok']);self.assertEqual(r.json()['error']['code'],'CAPABILITY_DISABLED')
 def test_harness_rejects_unauthenticated(self):
  os.environ['HARNESS_SERVICE_TOKEN']='a'*40
  r=TestClient(app).post('/internal/v4/tools/get_guest_profile',json={'guest_id':str(uuid4())})
  self.assertEqual(r.status_code,401)
 def test_write_requires_idempotency(self):
  os.environ['HARNESS_SERVICE_TOKEN']='a'*40
  r=TestClient(app).post('/internal/v4/tools/create_booking',json={'guest_id':str(uuid4()),'quote_id':str(uuid4()),'inventory_version':'v1'},headers={'Authorization':'Bearer '+'a'*40})
  self.assertEqual(r.status_code,422)
if __name__=='__main__':unittest.main()
