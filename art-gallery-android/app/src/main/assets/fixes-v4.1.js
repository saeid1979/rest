/* Rangin Gallery v4.1 stability layer */
(function(){
'use strict';
const $f=s=>document.querySelector(s), $$f=s=>[...document.querySelectorAll(s)];
let nativeReady=false;
function nativeLoad(key){try{if(window.AndroidBridge&&AndroidBridge.loadData){const x=AndroidBridge.loadData(key);return x||''}}catch(e){}return ''}
function nativeSave(key,obj){try{if(window.AndroidBridge&&AndroidBridge.saveData){AndroidBridge.saveData(key,typeof obj==='string'?obj:JSON.stringify(obj));return true}}catch(e){}return false}
function strippedWorks(){return works.map(w=>{const x=Object.assign({},w);delete x.image;delete x.extraImages;return x})}
function robustPersist(){
 const payload={version:41,works,cats,events,settings,lang,favs,inquiries,savedAt:Date.now()};
 nativeReady=nativeSave('core',payload)||nativeReady;
 try{localStorage.setItem(K.works,JSON.stringify(strippedWorks()))}catch(e){}
 try{localStorage.setItem(K.cats,JSON.stringify(cats))}catch(e){}
 try{localStorage.setItem(K.events,JSON.stringify(events.slice(-2000)))}catch(e){}
 try{localStorage.setItem(K.settings,JSON.stringify(settings))}catch(e){}
 try{localStorage.setItem(K.lang,lang||'en')}catch(e){}
 try{localStorage.setItem(K.favs,JSON.stringify(favs))}catch(e){}
 try{localStorage.setItem(K.inquiries,JSON.stringify(inquiries.slice(-500)))}catch(e){}
 updateStorageBadge();
}
function restoreNative(){
 const raw=nativeLoad('core');
 if(raw){
  try{
   const d=JSON.parse(raw);
   if(Array.isArray(d.works))works=d.works;
   if(Array.isArray(d.cats))cats=d.cats;
   if(Array.isArray(d.events))events=d.events;
   if(d.settings&&typeof d.settings==='object')settings=d.settings;
   if(Array.isArray(d.favs))favs=d.favs;
   if(Array.isArray(d.inquiries))inquiries=d.inquiries;
   if(d.lang&&['en','es','fa'].includes(d.lang)){lang=d.lang;try{localStorage.setItem(K.lang,lang)}catch(e){}}
   nativeReady=true;
   try{renderAll()}catch(e){}
   return;
  }catch(e){}
 }
 // First v4.1 run: migrate whatever the previous version still has.
 robustPersist();
}
function updateStorageBadge(){
 const el=$f('#v41Storage');if(!el)return;
 el.classList.toggle('bad',!nativeReady);
 el.textContent=nativeReady?
   (lang==='fa'?'ذخیره پایدار Android فعال است':lang==='es'?'Almacenamiento Android activo':'Android persistent storage active'):
   (lang==='fa'?'ذخیره پشتیبان مرورگر':lang==='es'?'Almacenamiento de respaldo':'Fallback storage');
}
function replaceImageCompressor(){
 try{
  imageToData=async function(file){
   return new Promise((resolve,reject)=>{
    const r=new FileReader();
    r.onload=()=>{const im=new Image();im.onload=()=>{
     const max=1200,sc=Math.min(1,max/Math.max(im.width,im.height)),cv=document.createElement('canvas');
     cv.width=Math.max(1,Math.round(im.width*sc));cv.height=Math.max(1,Math.round(im.height*sc));
     cv.getContext('2d').drawImage(im,0,0,cv.width,cv.height);
     resolve(cv.toDataURL('image/jpeg',.74));
    };im.onerror=reject;im.src=r.result};r.onerror=reject;r.readAsDataURL(file);
   });
  };
 }catch(e){}
}
function wireMainNav(){
 const nav=$f('.nav');if(!nav)return;
 nav.classList.add('v41-nav');
 let pb=$f('#v41ProTab');
 if(!pb){pb=document.createElement('button');pb.id='v41ProTab';pb.className='v41-pro';pb.innerHTML='<b>✦</b><span>PRO</span>';nav.appendChild(pb)}
 pb.onclick=e=>{e.preventDefault();try{if(window.RanginPro)RanginPro.open()}catch(err){}};
 $$f('.nav button[data-page]').forEach(b=>{
   b.onclick=null;
   b.addEventListener('click',function(e){
    e.preventDefault();
    const p=this.dataset.page;
    $$f('.page').forEach(x=>x.classList.toggle('on',x.id===p));
    $$f('.nav button[data-page]').forEach(x=>x.classList.toggle('on',x===this));
    try{renderAll()}catch(err){}
   });
 });
}
function addHub(){
 if($f('#v41Hub'))return;
 const dash=$f('#dashboard');if(!dash)return;
 const intro=dash.querySelector('.artIntro');
 const hub=document.createElement('div');hub.id='v41Hub';hub.className='v41Hub';
 hub.innerHTML='<h3>Rangin Gallery Pro</h3><p id="v41HubText"></p><div class="v41Grid">'+
 '<button data-v41s="art">🎨 '+(lang==='fa'?'آثار':lang==='es'?'Arte':'Art')+'</button>'+
 '<button data-v41s="business">💶 '+(lang==='fa'?'فروش':lang==='es'?'Ventas':'Sales')+'</button>'+
 '<button data-v41s="audience">👥 '+(lang==='fa'?'مخاطب':lang==='es'?'Audiencia':'Audience')+'</button>'+
 '<button data-v41s="ai">✦ AI</button>'+
 '<button data-v41s="online">🌐 '+(lang==='fa'?'آنلاین':lang==='es'?'Online':'Online')+'</button>'+
 '<button data-v41s="security">🔒 '+(lang==='fa'?'امنیت':lang==='es'?'Seguridad':'Security')+'</button>'+
 '</div><div id="v41Storage" class="v41Storage"></div>';
 if(intro&&intro.nextSibling)intro.parentNode.insertBefore(hub,intro.nextSibling);else dash.prepend(hub);
 $$f('[data-v41s]').forEach(b=>b.onclick=()=>{try{if(window.RanginPro)RanginPro.section(b.dataset.v41s)}catch(e){}});
 refreshHub();
}
function refreshHub(){
 const p=$f('#v41HubText');if(p)p.textContent=lang==='fa'?'مدیریت حرفه‌ای آثار، فروش، مشتریان، AI، وب، امنیت و گزارش‌ها از این بخش در دسترس است.':lang==='es'?'Accede aquí a obras, ventas, clientes, IA, web, seguridad e informes.':'Access artworks, sales, clients, AI, web, security and reports here.';
 updateStorageBadge();
}
function fixProNav(){
 document.addEventListener('click',e=>{
  const b=e.target.closest('[data-ps]');
  if(!b)return;
  try{if(window.RanginPro){e.preventDefault();RanginPro.section(b.dataset.ps)}}catch(err){}
 },true);
}
function protectPersist(){
 try{persist=robustPersist}catch(e){}
}
function fixExtraFormPersistence(){
 const form=$f('#workForm');if(!form||form.dataset.v41capture)return;form.dataset.v41capture='1';
 form.addEventListener('submit',function(){
   const editId=editing;
   const snap={
    shortDescription:$f('#shortDescription')?.value.trim()||'',
    tags:($f('#tags')?.value||'').split(',').map(x=>x.trim()).filter(Boolean),
    collectionId:$f('#collectionSelect')?.value||'',
    videoUrl:$f('#videoUrl')?.value.trim()||'',
    discountPrice:$f('#discountPrice')?.value.trim()||'',
    signatureNote:$f('#signatureNote')?.value.trim()||'',
    vip:!!$f('#vipWork')?.checked
   };
   setTimeout(()=>{const target=editId?works.find(x=>x.id===editId):works[works.length-1];if(target){Object.assign(target,snap);robustPersist();try{renderAll()}catch(e){}}},200);
 },true);
}
function migrateAfterLanguage(){
 $$f('[data-lang],[data-setlang],[data-picklang]').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{refreshHub();wireMainNav()},120)));
}
function initFix(){
 replaceImageCompressor();protectPersist();restoreNative();wireMainNav();addHub();fixProNav();fixExtraFormPersistence();migrateAfterLanguage();
 setTimeout(()=>{try{renderAll()}catch(e){};updateStorageBadge()},100);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initFix);else initFix();
})();