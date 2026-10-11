import {getChatGPTUser} from '../../chatgpt-auth';
import {getDb} from '../../../db';
import {records,rewards} from '../../../db/schema';
import {and,eq} from 'drizzle-orm';
export const dynamic='force-dynamic';
const json=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store'}});
const roles=['company','guest','owner'];
export async function GET(request:Request){
 const u=await getChatGPTUser();if(!u)return json({error:'Требуется вход'},401);
 const role=new URL(request.url).searchParams.get('role')||'company';if(!roles.includes(role))return json({error:'Неверный кабинет'},400);
 const rows=await getDb().select().from(records).where(and(eq(records.owner,u.userId),eq(records.role,role)));
 const ledger=await getDb().select().from(rewards).where(and(eq(rewards.owner,u.userId),eq(rewards.role,role)));
 return json({records:rows.map(({owner,...r})=>({...r,payload:JSON.parse(r.payload)})),rewards:ledger.map(({owner,...r})=>r),rewardRate:5});
}
export async function POST(request:Request){
 const u=await getChatGPTUser();if(!u)return json({error:'Требуется вход'},401);
 if(request.headers.get('origin')!==new URL(request.url).origin)return json({error:'Недопустимый источник'},403);
 if(!request.headers.get('content-type')?.startsWith('application/json'))return json({error:'Ожидается JSON'},415);
 const raw=await request.text();if(raw.length>25000)return json({error:'Слишком большой запрос'},413);
 let data;try{data=JSON.parse(raw)}catch{return json({error:'Некорректный JSON'},400)}
 const {role,kind}=data,p=data.payload;if(!roles.includes(role)||!p)return json({error:'Неверные параметры'},400);
 let payload;
 if(kind==='profile'){
  if(typeof p.name!=='string'||!p.name.trim()||p.name.length>200)return json({error:'Укажите название или имя'},400);
  if(role==='company'&&!/^\d{10}(\d{2})?$/.test(p.inn))return json({error:'ИНН должен содержать 10 или 12 цифр'},400);
  payload={name:p.name.trim(),inn:role==='company'?p.inn:'',contact:String(p.contact||'').slice(0,200)};
 }else if(kind==='employee'&&role==='company'){
  if(typeof p.name!=='string'||!p.name.trim()||p.name.length>150)return json({error:'Укажите имя сотрудника'},400);
  payload={name:p.name.trim(),position:String(p.position||'').slice(0,150)};
 }else if(kind==='trip'&&role==='company'){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(p.begin)||!/^\d{4}-\d{2}-\d{2}$/.test(p.end)||p.end<=p.begin||!Array.isArray(p.apartments)||p.apartments.length<1||p.apartments.length>3||!Number.isInteger(p.adults)||p.adults<1||p.adults>30)return json({error:'Проверьте даты, гостей и квартиры'},400);
  const apartments=p.apartments.map((a:any)=>({id:a.id,address:String(a.address||'').slice(0,200),price:Number.isFinite(a.price)&&a.price>0?a.price:null}));
  if(apartments.some((a:any)=>!Number.isInteger(a.id)||a.id<1))return json({error:'Некорректная квартира'},400);
  payload={begin:p.begin,end:p.end,adults:p.adults,apartments,method:p.method==='card'?'card':'invoice',status:'draft',paymentStatus:'unconfirmed'};
 }else if(kind==='request'&&role==='guest'){
  if(typeof p.text!=='string'||p.text.trim().length<5||p.text.length>2000)return json({error:'Опишите обращение (5–2000 символов)'},400);
  payload={text:p.text.trim(),status:'draft'};
 }else return json({error:'Этот тип записи недоступен. Начисления и оплаты меняются только подтверждёнными серверными событиями.'},403);
 const db=getDb(),id=kind==='profile'?`${role}:profile:${u.userId}`:crypto.randomUUID();
 const row={id,owner:u.userId,role,kind,payload:JSON.stringify(payload),created:new Date().toISOString()};
 if(kind==='profile')await db.insert(records).values(row).onConflictDoUpdate({target:records.id,set:{payload:row.payload}});else await db.insert(records).values(row);
 return json({id},201);
}
