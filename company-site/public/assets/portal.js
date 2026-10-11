(()=>{
const nav=document.querySelector('header');if(nav){const a=document.createElement('a');a.href='/cabinet';a.className='btn outline';a.textContent='Личные кабинеты';nav.append(a)}
let choice=null;
document.addEventListener('click',event=>{const b=event.target.closest('[data-book]');if(b)choice=Number(b.dataset.book)});
function saveTrip(method){if(!liveQuery||!choice){alert('Сначала выберите даты, проверьте стоимость и выберите квартиру.');return}const a=catalogItems.find(a=>a.id===choice);if(!a){alert('Повторите подбор квартиры.');return}sessionStorage.setItem('welcome-company-trip',JSON.stringify({begin:liveQuery.begin_date,end:liveQuery.end_date,adults:liveQuery.guests.adults,apartments:[{id:a.id,address:a.address,price:a.price}],method}));location.href='/cabinet';}
const actions=document.querySelector('#payment-choice .actions');if(actions){const b=document.createElement('button');b.type='button';b.className='btn outline';b.textContent='Сохранить поездку в кабинет';b.onclick=()=>saveTrip('invoice');actions.append(b)}
const order=document.querySelector('#corporate-result .actions');if(order){const b=document.createElement('button');b.type='button';b.className='btn outline';b.textContent='Сохранить в кабинет компании';b.onclick=()=>{if(!checkOrder())return;const o=corporateOrder;sessionStorage.setItem('welcome-company-trip',JSON.stringify({begin:o.query.begin_date,end:o.query.end_date,adults:o.query.guests.adults,apartments:o.apartments.map(a=>({id:a.id,address:a.address,price:a.price})),method:'invoice'}));location.href='/cabinet'};order.append(b)}
})();
