
/* Rangin Gallery Professional Suite v4 */
(function(){
'use strict';
const V4K='rangin_v4_suite';
const V4DEFAULT={
  clients:[], sales:[], commissions:[], exhibitions:[], comments:[], newsletter:[], artists:[], collections:[],
  notifications:[], payments:{stripe:'',paypal:'',redsys:'',inPerson:true}, web:{publicUrl:'',adminUrl:'',syncUrl:''},
  ai:{endpoint:''}, security:{pin:'',kiosk:false,protect:false}, theme:'miniature', autoBackup:false, vipPin:'', shareCount:{}
};
let v4=(()=>{try{return Object.assign({},V4DEFAULT,JSON.parse(localStorage.getItem(V4K)||'{}'))}catch(e){return JSON.parse(JSON.stringify(V4DEFAULT))}})();
['clients','sales','commissions','exhibitions','comments','newsletter','artists','collections','notifications'].forEach(k=>{if(!Array.isArray(v4[k]))v4[k]=[]});
v4.payments=Object.assign({},V4DEFAULT.payments,v4.payments||{});v4.web=Object.assign({},V4DEFAULT.web,v4.web||{});v4.ai=Object.assign({},V4DEFAULT.ai,v4.ai||{});v4.security=Object.assign({},V4DEFAULT.security,v4.security||{});
const save4=()=>localStorage.setItem(V4K,JSON.stringify(v4));
const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)];
const id=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,7);
const tx=(en,es,fa)=>lang==='fa'?fa:lang==='es'?es:en;
const money=(n,c='€')=>n?String(n)+' '+c:'—';
const dateFmt=x=>new Date(x).toLocaleDateString(lang==='fa'?'fa-IR':lang==='es'?'es-ES':'en-GB');
const h=s=>esc(s??'');

function mountHeader(){
 const holder=document.querySelector('.hero .brandrow > div:last-child');
 if(holder&&!q('#openProSuite')){
   const b=document.createElement('button');b.id='openProSuite';b.className='proBtn';b.textContent='PRO';holder.prepend(b);b.onclick=openSuite;
 }
}
function injectWorkExtras(){
 const form=q('#workForm'); if(!form||q('#v4Extras'))return;
 const x=document.createElement('div');x.id='v4Extras';x.className='form';
 x.innerHTML='<div class="twocol"><input id="shortDescription" placeholder="'+tx('Short description','Descripción corta','توضیح کوتاه')+'"><input id="tags" placeholder="'+tx('Tags: nature, blue...','Etiquetas: naturaleza, azul...','برچسب‌ها: طبیعت، آبی...')+'"></div>'+
 '<div class="twocol"><select id="collectionSelect"><option value="">'+tx('No collection','Sin colección','بدون مجموعه')+'</option></select><input id="videoUrl" placeholder="'+tx('Video URL','URL de vídeo','لینک ویدئو')+'"></div>'+
 '<div class="twocol"><input id="discountPrice" inputmode="decimal" placeholder="'+tx('Special/discount price','Precio especial','قیمت ویژه/تخفیف')+'"><input id="signatureNote" placeholder="'+tx('Signature / provenance note','Firma / procedencia','یادداشت امضا / پیشینه')+'"></div>'+
 '<div class="switch"><span>'+tx('VIP collection','Colección VIP','مجموعه VIP')+'</span><input type="checkbox" id="vipWork"></div>'+
 '<label class="picker">'+tx('Add extra images (up to 4)','Añadir imágenes extra (máx. 4)','افزودن عکس‌های بیشتر (حداکثر ۴)')+'<input id="extraImages" type="file" accept="image/*" multiple style="display:none"></label>';
 const desc=q('#description'); desc.parentNode.insertBefore(x,desc);
}
function fillCollections(){
 const sel=q('#collectionSelect');if(!sel)return;
 const old=sel.value;sel.innerHTML='<option value="">'+tx('No collection','Sin colección','بدون مجموعه')+'</option>'+v4.collections.map(c=>'<option value="'+h(c.id)+'">'+h(c.name)+'</option>').join('');sel.value=old;
}
function patchWorkForm(){
 const form=q('#workForm');if(!form||window.__v4WorkPatched)return;window.__v4WorkPatched=true;
 const oldOpen=openEdit,oldReset=resetForm,oldSubmit=form.onsubmit;
 openEdit=function(wid){
   oldOpen(wid);const w=works.find(a=>a.id===wid)||{};fillCollections();
   q('#shortDescription').value=w.shortDescription||'';
   q('#tags').value=(w.tags||[]).join(', ');
   q('#collectionSelect').value=w.collectionId||'';
   q('#videoUrl').value=w.videoUrl||'';
   q('#discountPrice').value=w.discountPrice||'';
   q('#signatureNote').value=w.signatureNote||'';
   q('#vipWork').checked=!!w.vip;
 };
 resetForm=function(){
   oldReset();fillCollections();
   if(q('#shortDescription')){
     q('#shortDescription').value='';q('#tags').value='';q('#videoUrl').value='';
     q('#discountPrice').value='';q('#signatureNote').value='';q('#vipWork').checked=false;q('#collectionSelect').value='';
     if(q('#extraImages'))q('#extraImages').value='';
   }
 };
 form.onsubmit=async function(e){
   const editId=editing;
   const existing=editId?works.find(a=>a.id===editId):null;
   const snap={
     shortDescription:q('#shortDescription').value.trim(),
     tags:q('#tags').value.split(',').map(x=>x.trim()).filter(Boolean),
     collectionId:q('#collectionSelect').value,
     videoUrl:q('#videoUrl').value.trim(),
     discountPrice:q('#discountPrice').value.trim(),
     signatureNote:q('#signatureNote').value.trim(),
     vip:q('#vipWork').checked
   };
   let extras=[...(existing?.extraImages||[])];
   const files=[...(q('#extraImages')?.files||[])].slice(0,4);
   for(const file of files){try{extras.push(await imageToData(file))}catch(err){}}
   extras=extras.slice(-4);
   await oldSubmit.call(this,e);
   const target=editId?works.find(a=>a.id===editId):works[works.length-1];
   if(target){
     Object.assign(target,snap,{extraImages:extras});
     persist();
     try{renderAll()}catch(err){}
   }
 };
}
function suiteHtml(){
 return '<div id="proSuite" class="proShell"><div class="proHead"><div class="proHeadRow"><div><h2>Rangin Gallery Pro</h2><small>'+tx('Professional artist suite','Suite profesional del artista','مجموعه حرفه‌ای هنرمند')+'</small></div><button class="proBtn" id="closePro">'+tx('Close','Cerrar','بستن')+'</button></div></div>'+
 '<div class="proBody"><div class="proNav" id="proNav"></div><div id="proContent"></div></div></div>'+
 '<div id="presentation" class="presentation"><div class="presImg"><img id="presImage"></div><div class="presFoot"><div id="presTitle" class="presTitle"></div><div id="presMeta"></div><div class="presBtns"><button id="presPrev">‹</button><button id="presPause">Ⅱ</button><button id="presNext">›</button><button id="presClose">×</button></div></div></div>'+
 '<div id="lockOverlay" class="lockOverlay"><div class="lockCard"><div class="bigRosette"><span>✦</span></div><h2>Rangin Gallery</h2><p>'+tx('Admin access','Acceso de administrador','دسترسی مدیر')+'</p><input id="unlockPin" type="password" inputmode="numeric" placeholder="PIN"><button class="goldbtn" id="unlockBtn" style="width:100%;margin-top:10px">'+tx('Unlock','Desbloquear','باز کردن')+'</button></div></div>';
}
const sections=[
 ['overview',tx('Overview','Resumen','نمای کلی')],['art',tx('Art Studio','Estudio','استودیو آثار')],['business',tx('Sales & CRM','Ventas y CRM','فروش و مشتریان')],
 ['events',tx('Events','Eventos','رویدادها')],['audience',tx('Audience','Audiencia','مخاطبان')],['ai',tx('AI & Search','IA y búsqueda','هوش مصنوعی و جستجو')],
 ['online',tx('Online','Online','آنلاین')],['security',tx('Security','Seguridad','امنیت')],['design',tx('Design','Diseño','طراحی')]
];
let activeSec='overview';
function openSuite(){q('#proSuite').classList.add('show');renderSuite()}
function renderNav(){q('#proNav').innerHTML=sections.map(x=>'<button data-ps="'+x[0]+'" class="'+(activeSec===x[0]?'on':'')+'">'+x[1]+'</button>').join('');qa('[data-ps]').forEach(b=>b.onclick=()=>{activeSec=b.dataset.ps;renderSuite()})}
function renderSuite(){renderNav();q('#proContent').innerHTML=renderSection(activeSec);bindSection()}
function artworkOptions(){return '<option value="">'+tx('Select artwork','Seleccionar obra','انتخاب اثر')+'</option>'+works.map(w=>'<option value="'+h(w.id)+'">'+h(w.title)+'</option>').join('')}
function calcStats(){
 const views=events.filter(e=>e.type==='view').length,favs=(typeof favs!=='undefined'?favs.length:0),inq=(typeof inquiries!=='undefined'?inquiries.length:0),sales=v4.sales.reduce((a,b)=>a+(+b.amount||0),0);
 return {views,favs,inq,sales,clients:v4.clients.length,works:works.length,published:works.filter(w=>w.published).length};
}
function renderSection(s){
 const st=calcStats();
 if(s==='overview')return '<div class="proGrid wide">'+[
  [st.works,tx('Artworks','Obras','آثار')],[st.published,tx('Published','Publicadas','منتشرشده')],[st.views,tx('Views','Visitas','بازدید')],[st.favs,tx('Favorites','Favoritos','علاقه‌مندی')],
  [st.inq,tx('Inquiries','Consultas','درخواست‌ها')],[st.clients,tx('Clients','Clientes','مشتریان')],[money(st.sales,'€'),tx('Recorded sales','Ventas registradas','فروش ثبت‌شده')],[v4.newsletter.length,tx('Newsletter','Boletín','خبرنامه')]
 ].map(x=>'<div class="proCard"><div class="proMetric">'+x[0]+'</div><p>'+x[1]+'</p></div>').join('')+
 '<div class="proCard" style="grid-column:1/-1"><h3>'+tx('Top performance','Mejor rendimiento','عملکرد برتر')+'</h3>'+topPerformance()+'</div>'+
 '<div class="proCard" style="grid-column:1/-1"><h3>'+tx('Quick actions','Acciones rápidas','عملیات سریع')+'</h3><div class="proTabs"><button data-act="presentation">'+tx('Presentation','Presentación','ارائه')+'</button><button data-act="portfolio">'+tx('Portfolio mode','Modo portafolio','حالت پورتفولیو')+'</button><button data-act="exhibit">'+tx('Exhibition','Exposición','نمایشگاه')+'</button><button data-act="backup">'+tx('Full backup','Copia completa','پشتیبان کامل')+'</button></div></div>';
 if(s==='art')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Collections','Colecciones','مجموعه‌ها')+'</h3><div class="proForm"><input id="colName" placeholder="'+tx('Collection name','Nombre de colección','نام مجموعه')+'"><textarea id="colDesc" placeholder="'+tx('Description','Descripción','توضیحات')+'"></textarea><button class="goldbtn" id="addCollection">'+tx('Add collection','Añadir colección','افزودن مجموعه')+'</button></div><div class="proList" style="margin-top:8px">'+v4.collections.map(c=>'<div class="proItem"><b>'+h(c.name)+'</b><small>'+h(c.description||'')+'</small></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Multiple artists','Varios artistas','چند هنرمند')+'</h3><div class="proForm"><input id="artist4Name" placeholder="'+tx('Artist name','Nombre','نام هنرمند')+'"><input id="artist4Role" placeholder="'+tx('Style / role','Estilo / función','سبک / نقش')+'"><button class="goldbtn" id="addArtist4">'+tx('Add artist','Añadir artista','افزودن هنرمند')+'</button></div><div class="proList" style="margin-top:8px">'+v4.artists.map(a=>'<div class="proItem"><b>'+h(a.name)+'</b><small>'+h(a.role||'')+'</small></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Catalog & authenticity','Catálogo y autenticidad','کاتالوگ و اصالت')+'</h3><p>'+tx('Catalog numbers, inventory status, Certificate of Authenticity, QR and PDF are active in the main artwork editor.','Números de catálogo, estado, certificado, QR y PDF activos.','شماره کاتالوگ، وضعیت موجودی، گواهی اصالت، QR و PDF در ویرایشگر اصلی فعال است.')+'</p></div>'+
 '<div class="proCard"><h3>'+tx('Watermark & protection','Marca de agua','واترمارک و حفاظت')+'</h3><label class="switch"><span>'+tx('Watermark previews','Marca de agua','واترمارک پیش‌نمایش')+'</span><input id="watermarkToggle" type="checkbox" '+(v4.watermark?'checked':'')+'></label><p>'+tx('Use preview images for public presentation; keep originals in your backup.','Usa vistas previas públicas y conserva originales en copia.','برای نمایش عمومی از پیش‌نمایش استفاده کن و اصل فایل‌ها را در پشتیبان نگه دار.')+'</p></div>'+
 '<div class="proCard"><h3>'+tx('Smart similar works','Obras similares','آثار مشابه')+'</h3><select id="similarWork">'+artworkOptions()+'</select><div id="similarResult" class="proList" style="margin-top:8px"></div></div>'+
 '<div class="proCard"><h3>'+tx('VIP Collection','Colección VIP','مجموعه VIP')+'</h3><div class="proForm"><input id="vipPin" type="password" inputmode="numeric" value="'+h(v4.vipPin||'')+'" placeholder="VIP PIN"><button id="saveVipPin" class="soft">'+tx('Save VIP PIN','Guardar PIN VIP','ذخیره PIN ویژه')+'</button></div><p>'+tx('Mark artworks as VIP in the artwork editor.','Marca obras como VIP en el editor.','در ویرایشگر اثر، گزینه VIP را فعال کن.')+'</p></div>';
 if(s==='business')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Clients','Clientes','مشتریان')+'</h3><div class="proForm"><input id="clientName" placeholder="'+tx('Name','Nombre','نام')+'"><input id="clientContact" placeholder="'+tx('Email / phone','Email / teléfono','ایمیل / تلفن')+'"><textarea id="clientNote" placeholder="'+tx('Private note','Nota privada','یادداشت خصوصی')+'"></textarea><button class="goldbtn" id="addClient">'+tx('Add client','Añadir cliente','افزودن مشتری')+'</button></div><div class="proList" style="margin-top:8px">'+v4.clients.slice().reverse().map(c=>'<div class="proItem"><b>'+h(c.name)+'</b><small>'+h(c.contact||'')+'</small></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Sales & invoice','Ventas y factura','فروش و فاکتور')+'</h3><div class="proForm"><select id="saleWork">'+artworkOptions()+'</select><input id="saleBuyer" placeholder="'+tx('Buyer','Comprador','خریدار')+'"><input id="saleAmount" inputmode="decimal" placeholder="'+tx('Amount EUR','Importe EUR','مبلغ یورو')+'"><select id="saleStatus"><option value="paid">'+tx('Paid','Pagado','پرداخت شده')+'</option><option value="pending">'+tx('Pending','Pendiente','در انتظار')+'</option></select><button class="goldbtn" id="addSale">'+tx('Record sale','Registrar venta','ثبت فروش')+'</button></div><div class="proList" style="margin-top:8px">'+v4.sales.slice().reverse().slice(0,8).map(x=>'<div class="proItem"><b>'+h(x.buyer||'')+' · '+money(x.amount,'€')+'</b><small>'+dateFmt(x.time)+' · '+h(x.status)+'</small><button class="soft" data-invoice="'+h(x.id)+'" style="margin-top:6px">'+tx('Invoice PDF','Factura PDF','فاکتور PDF')+'</button></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Custom commissions','Encargos personalizados','سفارش اختصاصی')+'</h3><div class="proForm"><input id="commName" placeholder="'+tx('Client','Cliente','مشتری')+'"><input id="commBudget" placeholder="'+tx('Budget','Presupuesto','بودجه')+'"><input id="commSize" placeholder="'+tx('Size','Tamaño','اندازه')+'"><textarea id="commBrief" placeholder="'+tx('Subject / brief','Tema / descripción','موضوع / توضیح')+'"></textarea><button class="goldbtn" id="addCommission">'+tx('Add commission','Añadir encargo','ثبت سفارش')+'</button></div><div class="proList" style="margin-top:8px">'+v4.commissions.slice().reverse().map(c=>'<div class="proItem"><b>'+h(c.name)+'</b><small>'+h(c.budget)+' · '+h(c.size)+'</small><p>'+h(c.brief)+'</p></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Payments','Pagos','پرداخت‌ها')+'</h3><div class="proForm"><input id="stripeLink" value="'+h(v4.payments.stripe||'')+'" placeholder="Stripe payment link"><input id="paypalLink" value="'+h(v4.payments.paypal||'')+'" placeholder="PayPal.me / payment link"><input id="redsysLink" value="'+h(v4.payments.redsys||'')+'" placeholder="Redsys checkout URL"><button id="savePayments" class="soft">'+tx('Save payment settings','Guardar pagos','ذخیره تنظیمات پرداخت')+'</button></div><div class="proWarn">'+tx('Real card payments require your merchant accounts and secure server-side configuration.','Los pagos reales requieren cuentas de comercio y configuración segura del servidor.','پرداخت واقعی کارت نیاز به حساب پذیرنده و تنظیم امن سمت سرور دارد.')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Sales analytics','Analítica de ventas','آمار فروش')+'</h3>'+salesAnalytics()+'</div>';
 if(s==='events')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Exhibition calendar','Calendario de exposiciones','تقویم نمایشگاه')+'</h3><div class="proForm"><input id="eventName" placeholder="'+tx('Event name','Nombre del evento','نام رویداد')+'"><input id="eventDate" type="date"><input id="eventPlace" placeholder="'+tx('Venue / address','Lugar / dirección','محل / آدرس')+'"><input id="eventMap" placeholder="Google Maps URL"><button class="goldbtn" id="addEvent">'+tx('Add event','Añadir evento','افزودن رویداد')+'</button></div><div class="proList" style="margin-top:8px">'+v4.exhibitions.slice().sort((a,b)=>a.date.localeCompare(b.date)).map(e=>'<div class="proItem"><b>'+h(e.name)+'</b><small>'+h(e.date)+' · '+h(e.place)+'</small>'+(e.map?'<button class="soft" data-map="'+h(e.map)+'" style="margin-top:6px">'+tx('Map','Mapa','نقشه')+'</button>':'')+'</div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Presentation mode','Modo presentación','حالت ارائه')+'</h3><p>'+tx('Automatic full-screen slideshow for exhibitions and meetings.','Presentación automática a pantalla completa.','اسلایدشو تمام‌صفحه برای نمایشگاه و جلسه.')+'</p><button class="goldbtn" id="startPresentation">'+tx('Start presentation','Iniciar presentación','شروع ارائه')+'</button></div>'+
 '<div class="proCard"><h3>'+tx('Kiosk mode','Modo kiosco','حالت کیوسک')+'</h3><label class="switch"><span>'+tx('Lock exhibition with admin PIN','Bloquear exposición con PIN','قفل نمایشگاه با PIN مدیر')+'</span><input id="kioskToggle" type="checkbox" '+(v4.security.kiosk?'checked':'')+'></label><input id="kioskPin" type="password" inputmode="numeric" placeholder="'+tx('Admin PIN','PIN de administrador','PIN مدیر')+'" value="'+h(v4.security.pin||'')+'"><button id="saveKiosk" class="soft">'+tx('Save','Guardar','ذخیره')+'</button></div></div>';
 if(s==='audience')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Comments & ratings','Comentarios y valoraciones','نظرات و امتیازها')+'</h3><div class="proForm"><select id="commentWork">'+artworkOptions()+'</select><input id="commentName" placeholder="'+tx('Visitor name','Nombre del visitante','نام بازدیدکننده')+'"><select id="commentRating"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select><textarea id="commentText" placeholder="'+tx('Comment','Comentario','نظر')+'"></textarea><button class="goldbtn" id="addComment">'+tx('Submit for approval','Enviar para aprobación','ثبت برای تایید')+'</button></div><div class="proList" style="margin-top:8px">'+v4.comments.slice().reverse().map(c=>'<div class="proItem"><b>'+h(c.name)+' · '+('★'.repeat(+c.rating||0))+'</b><small>'+(c.approved?tx('Approved','Aprobado','تاییدشده'):tx('Pending approval','Pendiente','در انتظار تایید'))+'</small><p>'+h(c.text)+'</p><button class="soft" data-approve="'+h(c.id)+'">'+tx('Toggle approval','Cambiar aprobación','تغییر تایید')+'</button></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Newsletter','Boletín','خبرنامه')+'</h3><div class="proForm"><input id="newsEmail" type="email" placeholder="email@example.com"><button id="addNews" class="goldbtn">'+tx('Subscribe','Suscribir','عضویت')+'</button></div><div class="proList" style="margin-top:8px">'+v4.newsletter.map(n=>'<div class="proItem"><b>'+h(n.email)+'</b><small>'+dateFmt(n.time)+'</small></div>').join('')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Engagement leaderboard','Clasificación de interacción','رتبه‌بندی تعامل')+'</h3>'+engagementBoard()+'</div>'+
 '<div class="proCard"><h3>'+tx('Notifications center','Centro de notificaciones','مرکز اعلان‌ها')+'</h3><div class="proList">'+notificationList()+'</div></div></div>';
 if(s==='ai')return '<div class="proGrid"><div class="proCard aiBox"><h3 style="color:#fff">'+tx('AI Art Assistant','Asistente IA','دستیار هوش مصنوعی هنر')+'</h3><select id="aiWork">'+artworkOptions()+'</select><textarea id="aiPrompt" placeholder="'+tx('Ask for title, description, tags, translation or analysis…','Pide título, descripción, etiquetas, traducción o análisis…','عنوان، توضیح، برچسب، ترجمه یا تحلیل بخواهید…')+'"></textarea><button class="goldbtn" id="runAI">'+tx('Run AI','Ejecutar IA','اجرای AI')+'</button><div id="aiResult" class="proItem" style="margin-top:8px;color:#222"></div></div>'+
 '<div class="proCard"><h3>'+tx('AI connection','Conexión IA','اتصال AI')+'</h3><div class="proForm"><input id="aiEndpoint" value="'+h(v4.ai.endpoint||'')+'" placeholder="https://your-server/api/ai"><button id="saveAI" class="soft">'+tx('Save endpoint','Guardar endpoint','ذخیره آدرس')+'</button></div><div class="proWarn">'+tx('For privacy and API-key safety, the app connects to your own AI server endpoint instead of storing provider secrets in the APK.','Por seguridad, la app usa tu propio endpoint y no guarda claves del proveedor en el APK.','برای امنیت کلید API، اپ به سرور AI خودت وصل می‌شود و کلید سرویس‌دهنده داخل APK ذخیره نمی‌شود.')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Smart search','Búsqueda inteligente','جستجوی هوشمند')+'</h3><input id="smartSearch" placeholder="'+tx('Try: blue miniature, 2025, sold…','Ej.: miniatura azul, 2025, vendida…','مثلاً: مینیاتور آبی، ۲۰۲۵، فروخته‌شده…')+'"><div id="smartResults" class="proList" style="margin-top:8px"></div></div>'+
 '<div class="proCard"><h3>'+tx('Visual search','Búsqueda visual','جستجوی تصویری')+'</h3><p>'+tx('Image understanding is available when an AI endpoint is connected.','El análisis de imagen funciona al conectar el endpoint IA.','تحلیل تصویر پس از اتصال endpoint هوش مصنوعی فعال می‌شود.')+'</p><button class="soft" id="visualSearch">'+tx('Analyze selected artwork','Analizar obra seleccionada','تحلیل اثر انتخابی')+'</button></div></div>';
 if(s==='online')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Public website','Sitio público','وب‌سایت عمومی')+'</h3><div class="proForm"><input id="publicUrl" value="'+h(v4.web.publicUrl||'')+'" placeholder="https://gallery.example.com"><input id="adminUrl" value="'+h(v4.web.adminUrl||'')+'" placeholder="https://admin.example.com"><input id="syncUrl4" value="'+h(v4.web.syncUrl||'')+'" placeholder="https://api.example.com"><button id="saveWeb" class="goldbtn">'+tx('Save web settings','Guardar web','ذخیره وب')+'</button></div></div>'+
 '<div class="proCard"><h3>'+tx('Online sync & analytics','Sincronización y analítica','همگام‌سازی و آمار آنلاین')+'</h3><p>'+tx('The app already works offline. Connect a server to synchronize artworks, clients, sales, comments and visitor analytics across devices.','La app funciona offline; conecta un servidor para sincronizar datos y analítica entre dispositivos.','اپ آفلاین کار می‌کند؛ با اتصال سرور آثار، مشتریان، فروش، نظرات و آمار بین دستگاه‌ها همگام می‌شود.')+'</p><button id="pushSync" class="soft">'+tx('Send snapshot to server','Enviar datos al servidor','ارسال نسخه به سرور')+'</button><div id="sync4Msg" class="proItem" style="margin-top:8px"></div></div>'+
 '<div class="proCard"><h3>'+tx('Visitor analytics','Analítica de visitantes','آمار بازدیدکننده')+'</h3><div class="proWarn">'+tx('Country, city, referral source and cross-device unique visitors require the online analytics server. Local views remain available immediately.','País, ciudad, origen y visitantes únicos requieren servidor online.','کشور، شهر، منبع ورود و بازدیدکننده یکتا نیازمند سرور آمار آنلاین است.')+'</div></div>'+
 '<div class="proCard"><h3>'+tx('Public links & QR','Enlaces públicos y QR','لینک عمومی و QR')+'</h3><p>'+tx('Once a public website URL is set, artwork QR codes can point to its public pages.','Al configurar la web pública, los QR pueden apuntar a cada obra.','پس از تنظیم سایت عمومی، QR هر اثر می‌تواند به صفحه عمومی آن وصل شود.')+'</p></div></div>';
 if(s==='security')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Admin PIN','PIN de administrador','PIN مدیر')+'</h3><div class="proForm"><input id="adminPin4" type="password" inputmode="numeric" value="'+h(v4.security.pin||'')+'" placeholder="PIN"><button id="savePin4" class="goldbtn">'+tx('Save PIN','Guardar PIN','ذخیره PIN')+'</button></div></div>'+
 '<div class="proCard"><h3>'+tx('Biometric login','Acceso biométrico','ورود بیومتریک')+'</h3><p>'+tx('Fingerprint/face authentication uses the Android biometric system when available.','Usa el sistema biométrico de Android.','از سیستم بیومتریک اندروید برای اثر انگشت/چهره استفاده می‌شود.')+'</p><button id="testBio" class="soft">'+tx('Test biometric','Probar biometría','آزمایش بیومتریک')+'</button></div>'+
 '<div class="proCard"><h3>'+tx('Image protection','Protección de imagen','حفاظت تصویر')+'</h3><label class="switch"><span>'+tx('Block screenshots in protected mode','Bloquear capturas','مسدودکردن اسکرین‌شات در حالت محافظت')+'</span><input id="protectToggle" type="checkbox" '+(v4.security.protect?'checked':'')+'></label><p>'+tx('No method can fully prevent copying, but previews, watermarking and screenshot protection reduce casual reuse.','Ningún método evita totalmente la copia; estas medidas reducen el uso casual.','هیچ روشی کپی را کاملاً متوقف نمی‌کند، اما پیش‌نمایش، واترمارک و جلوگیری از اسکرین‌شات کمک می‌کند.')+'</p></div>'+
 '<div class="proCard"><h3>'+tx('Full backup','Copia completa','پشتیبان کامل')+'</h3><p>'+tx('Artwork images are stored inside the backup JSON as data, so the backup contains your local gallery data.','Las imágenes se incluyen como datos dentro del JSON.','تصاویر به‌صورت داده داخل JSON ذخیره می‌شوند و پشتیبان اطلاعات گالری را همراه دارد.')+'</p><button id="backup4" class="goldbtn">'+tx('Export full backup','Exportar copia completa','خروجی پشتیبان کامل')+'</button></div></div>';
 if(s==='design')return '<div class="proGrid"><div class="proCard"><h3>'+tx('Art themes','Temas artísticos','تم‌های هنری')+'</h3><div class="proTabs"><button data-theme4="miniature">Miniature</button><button data-theme4="turquoise">Turquoise</button><button data-theme4="gold">Gold</button><button data-theme4="dark">Dark Art</button></div></div>'+
 '<div class="proCard"><h3>'+tx('Portfolio mode','Modo portafolio','حالت پورتفولیو')+'</h3><p>'+tx('A clean client-facing view without management controls.','Vista limpia para clientes sin controles de administración.','نمای تمیز برای مشتری بدون ابزار مدیریت.')+'</p><button id="portfolio4" class="goldbtn">'+tx('Open portfolio','Abrir portafolio','بازکردن پورتفولیو')+'</button></div>'+
 '<div class="proCard"><h3>'+tx('Brand identity','Identidad visual','هویت بصری')+'</h3><p>Rangin Gallery · Persian miniature inspired · English / Español / فارسی</p><span class="proBadge">Lapis</span><span class="proBadge">Turquoise</span><span class="proBadge">Gold</span><span class="proBadge">Persian Red</span></div></div>';
 return '';
}
function topPerformance(){
 const arr=works.map(w=>({w,v:events.filter(e=>e.type==='view'&&e.workId===w.id).length,f:(typeof favs!=='undefined'&&favs.includes(w.id))?1:0,i:(typeof inquiries!=='undefined'?inquiries.filter(x=>x.workId===w.id).length:0),s:v4.sales.filter(x=>x.workId===w.id).length})).sort((a,b)=>(b.v+b.f*3+b.i*4+b.s*6)-(a.v+a.f*3+a.i*4+a.s*6)).slice(0,6);
 return '<table class="proTable"><tr><th>'+tx('Artwork','Obra','اثر')+'</th><th>'+tx('Views','Visitas','بازدید')+'</th><th>♥</th><th>'+tx('Leads','Consultas','درخواست')+'</th><th>'+tx('Sales','Ventas','فروش')+'</th></tr>'+arr.map(x=>'<tr><td>'+h(x.w.title)+'</td><td>'+x.v+'</td><td>'+x.f+'</td><td>'+x.i+'</td><td>'+x.s+'</td></tr>').join('')+'</table>';
}
function salesAnalytics(){
 const total=v4.sales.reduce((a,b)=>a+(+b.amount||0),0),paid=v4.sales.filter(x=>x.status==='paid').reduce((a,b)=>a+(+b.amount||0),0);
 return '<div class="proMetric">'+money(total,'€')+'</div><p>'+tx('Total recorded','Total registrado','کل ثبت‌شده')+'</p><div class="proOk">'+tx('Paid','Pagado','پرداخت شده')+': '+money(paid,'€')+' · '+tx('Sales','Ventas','فروش')+': '+v4.sales.length+'</div>';
}
function engagementBoard(){
 return works.map(w=>({w,score:events.filter(e=>e.workId===w.id&&e.type==='view').length+((typeof favs!=='undefined'&&favs.includes(w.id))?3:0)+(typeof inquiries!=='undefined'?inquiries.filter(x=>x.workId===w.id).length*4:0)+(v4.shareCount[w.id]||0)*2})).sort((a,b)=>b.score-a.score).slice(0,8).map((x,i)=>'<div class="proItem"><b>#'+(i+1)+' '+h(x.w.title)+'</b><small>'+tx('Engagement score','Puntuación','امتیاز تعامل')+': '+x.score+'</small></div>').join('');
}
function notificationList(){
 const dynamic=[];
 if(typeof inquiries!=='undefined'&&inquiries.length)dynamic.push({text:tx('You have '+inquiries.length+' artwork inquiries.','Tienes '+inquiries.length+' consultas.','شما '+inquiries.length+' درخواست درباره آثار دارید.')});
 if(v4.commissions.length)dynamic.push({text:tx('Custom commissions: '+v4.commissions.length,'Encargos: '+v4.commissions.length,'سفارش اختصاصی: '+v4.commissions.length)});
 return [...dynamic,...v4.notifications].slice(0,8).map(n=>'<div class="proItem">'+h(n.text)+'</div>').join('')||'<div class="proItem">'+tx('No new notifications','Sin notificaciones nuevas','اعلان جدیدی نیست')+'</div>';
}
function bindSection(){
 q('#closePro').onclick=()=>q('#proSuite').classList.remove('show');
 qa('[data-act]').forEach(b=>b.onclick=()=>{if(b.dataset.act==='presentation')startPresentation();if(b.dataset.act==='portfolio'&&q('#previewGallery'))q('#previewGallery').click();if(b.dataset.act==='exhibit'&&q('#openExhibit'))q('#openExhibit').click();if(b.dataset.act==='backup')exportFullBackup()});
 if(q('#addCollection'))q('#addCollection').onclick=()=>{const n=q('#colName').value.trim();if(!n)return;v4.collections.push({id:id(),name:n,description:q('#colDesc').value.trim()});save4();fillCollections();renderSuite()};
 if(q('#addArtist4'))q('#addArtist4').onclick=()=>{const n=q('#artist4Name').value.trim();if(!n)return;v4.artists.push({id:id(),name:n,role:q('#artist4Role').value.trim()});save4();renderSuite()};
 if(q('#watermarkToggle'))q('#watermarkToggle').onchange=e=>{v4.watermark=e.target.checked;save4();document.body.classList.toggle('watermarkPreview',v4.watermark)};
 if(q('#saveVipPin'))q('#saveVipPin').onclick=()=>{v4.vipPin=q('#vipPin').value;save4()};
 if(q('#similarWork'))q('#similarWork').onchange=e=>renderSimilar(e.target.value);
 if(q('#addClient'))q('#addClient').onclick=()=>{const n=q('#clientName').value.trim();if(!n)return;v4.clients.push({id:id(),name:n,contact:q('#clientContact').value.trim(),note:q('#clientNote').value.trim(),time:Date.now()});save4();renderSuite()};
 if(q('#addSale'))q('#addSale').onclick=()=>{const amt=q('#saleAmount').value.trim(),buyer=q('#saleBuyer').value.trim();if(!buyer&&!amt)return;v4.sales.push({id:id(),workId:q('#saleWork').value,buyer,amount:amt,status:q('#saleStatus').value,time:Date.now()});const w=works.find(x=>x.id===q('#saleWork').value);if(w&&q('#saleStatus').value==='paid'){w.inventoryStatus='sold';persist()}save4();renderSuite()};
 qa('[data-invoice]').forEach(b=>b.onclick=()=>printInvoice(b.dataset.invoice));
 if(q('#addCommission'))q('#addCommission').onclick=()=>{const n=q('#commName').value.trim();if(!n)return;v4.commissions.push({id:id(),name:n,budget:q('#commBudget').value.trim(),size:q('#commSize').value.trim(),brief:q('#commBrief').value.trim(),time:Date.now()});save4();renderSuite()};
 if(q('#savePayments'))q('#savePayments').onclick=()=>{v4.payments.stripe=q('#stripeLink').value.trim();v4.payments.paypal=q('#paypalLink').value.trim();v4.payments.redsys=q('#redsysLink').value.trim();save4();toast(tx('Saved','Guardado','ذخیره شد'))};
 if(q('#addEvent'))q('#addEvent').onclick=()=>{const n=q('#eventName').value.trim();if(!n)return;v4.exhibitions.push({id:id(),name:n,date:q('#eventDate').value,place:q('#eventPlace').value.trim(),map:q('#eventMap').value.trim()});save4();renderSuite()};
 qa('[data-map]').forEach(b=>b.onclick=()=>openExternal(b.dataset.map));
 if(q('#startPresentation'))q('#startPresentation').onclick=startPresentation;
 if(q('#saveKiosk'))q('#saveKiosk').onclick=()=>{v4.security.kiosk=q('#kioskToggle').checked;v4.security.pin=q('#kioskPin').value.trim();save4()};
 if(q('#addComment'))q('#addComment').onclick=()=>{const text=q('#commentText').value.trim();if(!text)return;v4.comments.push({id:id(),workId:q('#commentWork').value,name:q('#commentName').value.trim()||'Visitor',rating:q('#commentRating').value,text,approved:false,time:Date.now()});save4();renderSuite()};
 qa('[data-approve]').forEach(b=>b.onclick=()=>{const c=v4.comments.find(x=>x.id===b.dataset.approve);if(c)c.approved=!c.approved;save4();renderSuite()});
 if(q('#addNews'))q('#addNews').onclick=()=>{const e=q('#newsEmail').value.trim();if(!e)return;v4.newsletter.push({id:id(),email:e,time:Date.now()});save4();renderSuite()};
 if(q('#saveAI'))q('#saveAI').onclick=()=>{v4.ai.endpoint=q('#aiEndpoint').value.trim();save4()};
 if(q('#runAI'))q('#runAI').onclick=runAI;
 if(q('#smartSearch'))q('#smartSearch').oninput=e=>smartSearch(e.target.value);
 if(q('#visualSearch'))q('#visualSearch').onclick=()=>{q('#aiResult')&&(q('#aiResult').textContent=tx('Select an artwork above and connect your AI endpoint for visual analysis.','Selecciona una obra y conecta el endpoint IA.','برای تحلیل تصویری یک اثر انتخاب و endpoint هوش مصنوعی را متصل کنید.'))};
 if(q('#saveWeb'))q('#saveWeb').onclick=()=>{v4.web.publicUrl=q('#publicUrl').value.trim();v4.web.adminUrl=q('#adminUrl').value.trim();v4.web.syncUrl=q('#syncUrl4').value.trim();save4()};
 if(q('#pushSync'))q('#pushSync').onclick=pushSync;
 if(q('#savePin4'))q('#savePin4').onclick=()=>{v4.security.pin=q('#adminPin4').value.trim();save4()};
 if(q('#testBio'))q('#testBio').onclick=testBiometric;
 if(q('#protectToggle'))q('#protectToggle').onchange=e=>{v4.security.protect=e.target.checked;save4();try{if(window.AndroidBridge&&AndroidBridge.setSecureScreen)AndroidBridge.setSecureScreen(v4.security.protect)}catch(err){}};
 if(q('#backup4'))q('#backup4').onclick=exportFullBackup;
 qa('[data-theme4]').forEach(b=>b.onclick=()=>applyTheme(b.dataset.theme4));
 if(q('#portfolio4'))q('#portfolio4').onclick=()=>q('#previewGallery')&&q('#previewGallery').click();
}
function renderSimilar(wid){
 const w=works.find(x=>x.id===wid),box=q('#similarResult');if(!w||!box)return;
 const tags=w.tags||[];const a=works.filter(x=>x.id!==wid).map(x=>({x,score:(x.category===w.category?3:0)+(x.technique&&x.technique===w.technique?3:0)+(x.tags||[]).filter(t=>tags.includes(t)).length*2})).sort((a,b)=>b.score-a.score).slice(0,5);
 box.innerHTML=a.map(z=>'<div class="proItem"><b>'+h(z.x.title)+'</b><small>'+tx('Similarity','Similitud','شباهت')+': '+z.score+'</small></div>').join('');
}
function smartSearch(term){
 const box=q('#smartResults');if(!box)return;term=term.trim().toLowerCase();if(!term){box.innerHTML='';return}
 const a=works.filter(w=>[w.title,w.description,w.shortDescription,w.category,w.technique,w.year,w.inventoryStatus,(w.tags||[]).join(' ')].join(' ').toLowerCase().includes(term)).slice(0,12);
 box.innerHTML=a.map(w=>'<div class="proItem"><b>'+h(w.title)+'</b><small>'+h(w.category||'')+' · '+h(w.technique||'')+' · '+h(statusLabel(w.inventoryStatus))+'</small></div>').join('')||'<div class="proItem">'+tx('No matches','Sin resultados','نتیجه‌ای یافت نشد')+'</div>';
}
async function runAI(){
 const box=q('#aiResult'),endpoint=v4.ai.endpoint,prompt=q('#aiPrompt').value.trim(),wid=q('#aiWork').value,w=works.find(x=>x.id===wid);
 if(!endpoint){box.textContent=tx('Connect your AI server endpoint first.','Conecta primero tu endpoint IA.','ابتدا endpoint سرور هوش مصنوعی را متصل کنید.');return}
 box.textContent=tx('Working…','Procesando…','در حال پردازش…');
 try{const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:prompt,artwork:w||null,language:lang})});const data=await r.json();box.textContent=data.text||data.result||JSON.stringify(data)}catch(e){box.textContent=tx('AI connection failed.','Falló la conexión IA.','اتصال هوش مصنوعی ناموفق بود.')}
}
async function pushSync(){
 const box=q('#sync4Msg');if(!v4.web.syncUrl){box.textContent=tx('Set the sync server URL first.','Configura primero la URL del servidor.','ابتدا آدرس سرور همگام‌سازی را تنظیم کنید.');return}
 try{const payload={works,categories:cats,settings,pro:v4,events};const r=await fetch(v4.web.syncUrl.replace(/\/$/,'')+'/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});box.textContent=r.ok?tx('Sync completed.','Sincronización completada.','همگام‌سازی انجام شد.'):tx('Server returned an error.','El servidor devolvió un error.','سرور خطا برگرداند.')}catch(e){box.textContent=tx('Could not connect to server.','No se pudo conectar al servidor.','اتصال به سرور برقرار نشد.')}
}
function openExternal(url){if(!url)return;try{if(window.AndroidBridge&&AndroidBridge.openExternal){AndroidBridge.openExternal(url);return}}catch(e){}location.href=url}
function exportFullBackup(){const data={format:'RanginGalleryFullBackup',version:4,time:new Date().toISOString(),works,cats,events,settings,pro:v4,favorites:(typeof favs!=='undefined'?favs:[]),inquiries:(typeof inquiries!=='undefined'?inquiries:[])};download('Rangin-Gallery-FULL-BACKUP.json',JSON.stringify(data,null,2))}
function printInvoice(sid){
 const x=v4.sales.find(a=>a.id===sid);if(!x)return;const w=works.find(a=>a.id===x.workId),a=settings.artist||{};
 q('#printArea').innerHTML='<div style="font-family:Arial;padding:25px"><h1>Rangin Gallery</h1><h2>'+tx('Invoice','Factura','فاکتور')+'</h2><p><b>#</b> '+h(x.id)+'</p><p><b>'+tx('Artist','Artista','هنرمند')+':</b> '+h(a.name||'Rangin Artist')+'</p><p><b>'+tx('Buyer','Comprador','خریدار')+':</b> '+h(x.buyer)+'</p><p><b>'+tx('Artwork','Obra','اثر')+':</b> '+h(w?.title||'—')+'</p><p><b>'+tx('Amount','Importe','مبلغ')+':</b> '+money(x.amount,'€')+'</p><p><b>'+tx('Status','Estado','وضعیت')+':</b> '+h(x.status)+'</p><p><b>'+tx('Date','Fecha','تاریخ')+':</b> '+dateFmt(x.time)+'</p></div>';
 setTimeout(()=>nativePrint('Rangin Invoice '+x.id),250);
}
let presIndex=0,presTimer=null,presPaused=false;
function startPresentation(){
 const arr=works.filter(w=>w.published&&!w.vip);if(!arr.length)return;presIndex=0;q('#presentation').classList.add('show');showPres(arr);
 clearInterval(presTimer);presPaused=false;presTimer=setInterval(()=>{if(!presPaused){presIndex=(presIndex+1)%arr.length;showPres(arr)}},6000);
}
function showPres(arr){const w=arr[presIndex];q('#presImage').src=w.image||'';q('#presTitle').textContent=w.title||'';q('#presMeta').textContent=[w.category,w.year,w.technique].filter(Boolean).join(' · ')}
function bindPresentation(){
 q('#presPrev').onclick=()=>{const a=works.filter(w=>w.published&&!w.vip);presIndex=(presIndex-1+a.length)%a.length;showPres(a)};
 q('#presNext').onclick=()=>{const a=works.filter(w=>w.published&&!w.vip);presIndex=(presIndex+1)%a.length;showPres(a)};
 q('#presPause').onclick=()=>{presPaused=!presPaused;q('#presPause').textContent=presPaused?'▶':'Ⅱ'};
 q('#presClose').onclick=()=>{if(v4.security.kiosk){q('#lockOverlay').classList.add('show');return}q('#presentation').classList.remove('show');clearInterval(presTimer)};
 q('#unlockBtn').onclick=()=>{if(q('#unlockPin').value===v4.security.pin){q('#lockOverlay').classList.remove('show');q('#presentation').classList.remove('show');q('#unlockPin').value='';clearInterval(presTimer)}else{q('#unlockPin').value=''}};
}
function applyTheme(th){document.documentElement.classList.remove('theme-dark','theme-turquoise','theme-gold','theme-miniature');document.documentElement.classList.add('theme-'+th);v4.theme=th;save4()}
function testBiometric(){try{if(window.AndroidBridge&&AndroidBridge.authenticateBiometric){AndroidBridge.authenticateBiometric();return}}catch(e){}toast(tx('Biometric bridge unavailable on this build.','Biometría no disponible en esta compilación.','بیومتریک در این نسخه اندروید در دسترس نیست.'))}
window.onBiometricResult=function(ok){toast(ok?tx('Biometric authentication successful.','Autenticación correcta.','احراز هویت بیومتریک موفق بود.'):tx('Biometric authentication failed.','Autenticación fallida.','احراز هویت بیومتریک ناموفق بود.'))};
function patchViewer(){
 if(q('#shareArtwork')&&!window.__v4SharePatch){window.__v4SharePatch=true;const old=q('#shareArtwork').onclick;q('#shareArtwork').onclick=async function(){if(viewerWorkId)v4.shareCount[viewerWorkId]=(v4.shareCount[viewerWorkId]||0)+1;save4();if(old)return old.apply(this,arguments)}}
}
function patchExhibit(){
 const old=window.renderExhibit||null;
 if(typeof renderExhibit==='function'&&!window.__v4ExPatched){window.__v4ExPatched=true;const base=renderExhibit;renderExhibit=function(){base();qa('.guestCard').forEach(card=>{const wid=card.querySelector('[data-guest]')?.dataset.guest,w=works.find(x=>x.id===wid);if(w?.vip){const m=document.createElement('div');m.className='vipMark';m.textContent='VIP';card.appendChild(m)}if(v4.watermark)card.classList.add('watermarkPreview')})}}
}
function addPaymentButtons(){
 if(!q('#viewerModal')||q('#v4PayBtns'))return;
 const foot=q('#viewerModal .foot');if(!foot)return;const d=document.createElement('div');d.id='v4PayBtns';d.className='proTabs';d.style.marginTop='8px';d.innerHTML='<button id="reserveArtwork">'+tx('Reserve','Reservar','رزرو')+'</button><button id="buyArtwork">'+tx('Buy / pay','Comprar / pagar','خرید / پرداخت')+'</button>';foot.parentNode.appendChild(d);
 q('#reserveArtwork').onclick=()=>{const w=works.find(x=>x.id===viewerWorkId);if(w){w.inventoryStatus='reserved';persist();renderAll();toast(tx('Artwork reserved.','Obra reservada.','اثر رزرو شد.'))}};
 q('#buyArtwork').onclick=()=>{const u=v4.payments.stripe||v4.payments.paypal||v4.payments.redsys;if(u)openExternal(u);else q('#inquireArtwork')?.click()};
}
function init(){
 document.body.insertAdjacentHTML('beforeend',suiteHtml());mountHeader();injectWorkExtras();fillCollections();patchWorkForm();patchViewer();patchExhibit();addPaymentButtons();bindPresentation();applyTheme(v4.theme||'miniature');document.body.classList.toggle('watermarkPreview',!!v4.watermark);
 q('#closePro').onclick=()=>q('#proSuite').classList.remove('show');
 qa('[data-lang],[data-setlang]').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{mountHeader();renderSuite()},50)));
}
window.RanginPro={open:openSuite,refresh:renderSuite,section:function(name){activeSec=name;openSuite();renderSuite();}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
