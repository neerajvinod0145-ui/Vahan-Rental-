const $ = (id) => document.getElementById(id);
let currentUser = null;
let vehiclesCache = [];
const today = new Date().toISOString().slice(0,10);

async function api(url, options={}) {
  const response = await fetch(url, {credentials:'same-origin', headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options});
  const data = await response.json().catch(()=>({error:'Unexpected server response.'}));
  if (!response.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}
function toast(message){const el=$('toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2800)}
function openModal(html){$('modalContent').innerHTML=html;$('modal').classList.remove('hidden')}
function closeModal(){$('modal').classList.add('hidden')}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function updateHeader(){
  const logged=!!currentUser;
  $('loginBtn').classList.toggle('hidden',logged);$('signupBtn').classList.toggle('hidden',logged);
  $('dashboardBtn').classList.toggle('hidden',!logged);$('logoutBtn').classList.toggle('hidden',!logged);
  $('welcome').textContent=logged?`Hi, ${currentUser.name}`:'';
}
async function loadUser(){try{const d=await api('/api/me');currentUser=d.user;updateHeader()}catch(e){console.error(e)}}
async function loadVehicles(){
  const search=$('searchInput').value.trim(), category=$('categoryFilter').value;
  $('vehicleGrid').innerHTML='<div class="loading">Finding available rides...</div>';
  try{const d=await api(`/api/vehicles?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}`);vehiclesCache=d.vehicles;renderVehicles()}
  catch(e){$('vehicleGrid').innerHTML=`<div class="empty">${escapeHtml(e.message)} Please refresh the page.</div>`}
}
function renderVehicles(){
  if(!vehiclesCache.length){$('vehicleGrid').innerHTML='<div class="empty">No vehicles found. Try another search.</div>';return}
  $('vehicleGrid').innerHTML=vehiclesCache.map(v=>`<article class="vehicle-card"><div class="vehicle-visual"><span class="tag">${escapeHtml(v.category)}</span>${escapeHtml(v.image||'🚘')}</div><div class="vehicle-info"><h3>${escapeHtml(v.name)}</h3><div class="vehicle-meta"><span>◷ ${escapeHtml(v.model)}</span><span>⌖ ${escapeHtml(v.location)}</span></div><p style="font-size:11px;color:#718096;line-height:1.6">${escapeHtml(v.description)}</p><div class="vehicle-bottom"><div class="price">₹${Number(v.price).toLocaleString('en-IN')} <small>/ day</small></div><button class="btn btn-primary" onclick="bookVehicle(${v.id})">Book now →</button></div></div></article>`).join('');
}
function authModal(mode='login'){
 const signup=mode==='signup';
 openModal(`<h2>${signup?'Create your account':'Welcome back'}</h2><p>${signup?'Join VahanaShare and find your next ride.':'Log in to manage your bookings and explore vehicles.'}</p><form id="authForm">${signup?'<div class="field"><label>Full name</label><input name="name" required placeholder="Your name"></div>':''}<div class="field"><label>Email address</label><input name="email" type="email" required placeholder="you@example.com"></div><div class="field"><label>Password</label><input name="password" type="password" minlength="6" required placeholder="At least 6 characters"></div><button class="btn btn-primary" type="submit">${signup?'Create account':'Log in'} →</button></form><div class="switch-auth">${signup?'Already registered?':'New to VahanaShare?'} <a id="switchAuth">${signup?'Log in':'Create an account'}</a></div>`);
 $('switchAuth').onclick=()=>authModal(signup?'login':'signup');
 $('authForm').onsubmit=async e=>{e.preventDefault();const form=Object.fromEntries(new FormData(e.target));try{const d=await api(signup?'/api/register':'/api/login',{method:'POST',body:JSON.stringify(form)});currentUser=d.user;updateHeader();closeModal();toast(d.message);loadVehicles()}catch(err){toast(err.message)}};
}
function bookVehicle(id){
 if(!currentUser){toast('Please log in to book a vehicle.');authModal('login');return}
 const v=vehiclesCache.find(x=>x.id===id);if(!v)return;
 openModal(`<h2>Book ${escapeHtml(v.name)}</h2><p>₹${Number(v.price).toLocaleString('en-IN')} per day · ${escapeHtml(v.location)}</p><form id="bookingForm"><div class="field"><label>Start date</label><input type="date" name="start_date" min="${today}" value="${today}" required></div><div class="field"><label>End date</label><input type="date" name="end_date" min="${today}" value="${today}" required></div><button class="btn btn-primary">Confirm booking →</button></form>`);
 $('bookingForm').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));try{const result=await api('/api/bookings',{method:'POST',body:JSON.stringify({...d,vehicle_id:id})});closeModal();toast(`${result.message} Total: ₹${result.total}`)}catch(err){toast(err.message)}};
}
async function account(){
 if(!currentUser)return authModal();
 openModal(`<h2>${currentUser.role==='admin'?'Admin dashboard':'My account'}</h2><p>Signed in as ${escapeHtml(currentUser.email)}</p><div class="account-tabs"><button class="active" data-tab="bookings">Bookings</button><button data-tab="notifications">Notifications</button>${currentUser.role==='admin'?'<button data-tab="admin">Admin</button>':''}</div><div id="accountContent" class="account-list">Loading...</div>`);
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.remove('active'));b.classList.add('active');loadAccountTab(b.dataset.tab)});
 loadAccountTab('bookings');
}
async function loadAccountTab(tab){const box=$('accountContent');if(!box)return;box.innerHTML='<div class="loading">Loading...</div>';
 try{
  if(tab==='bookings'){
   const d=await api('/api/bookings');box.innerHTML=d.bookings.length?d.bookings.map(b=>`<div class="account-item"><div><b>${escapeHtml(b.vehicle_name)}</b><br>${escapeHtml(b.start_date)} → ${escapeHtml(b.end_date)}<br><span style="color:#718096">${currentUser.role==='admin'?'Customer: '+escapeHtml(b.user_name)+' · ':''}₹${Number(b.total).toLocaleString('en-IN')} · ${escapeHtml(b.status)}</span></div>${currentUser.role==='admin'&&b.status==='Confirmed'?`<button class="btn btn-outline" onclick="cancelBooking(${b.id})">Cancel</button>`:''}</div>`).join(''):'<div class="empty">No bookings yet.</div>';
  }else if(tab==='notifications'){
   const d=await api('/api/notifications');box.innerHTML=d.notifications.length?d.notifications.map(n=>`<div class="account-item"><span>${escapeHtml(n.message)}</span><small>${escapeHtml(n.created_at)}</small></div>`).join(''):'<div class="empty">No notifications yet.</div>';
  }else if(tab==='admin'){
   const [s,b]=await Promise.all([api('/api/admin/stats'),api('/api/bookings')]);
   box.innerHTML=`<div class="admin-stats"><div><b>${s.users}</b><span>Registered users</span></div><div><b>${s.vehicles}</b><span>Total vehicles</span></div><div><b>${s.bookings}</b><span>Total bookings</span></div><div><b>₹${Number(s.revenue).toLocaleString('en-IN')}</b><span>Confirmed booking value</span></div></div><h3 style="font:700 15px Manrope;margin:22px 0 5px">Add a vehicle</h3><form id="addVehicle"><div class="field"><label>Vehicle name</label><input name="name" required></div><div class="field"><label>Category</label><select name="category"><option>Bike</option><option>Scooter</option><option>Car</option></select></div><div class="field"><label>Model / year</label><input name="model" required></div><div class="field"><label>Price per day (₹)</label><input name="price" type="number" min="1" required></div><div class="field"><label>Location</label><input name="location" required></div><div class="field"><label>Description</label><input name="description"></div><button class="btn btn-primary">Add vehicle +</button></form><h3 style="font:700 15px Manrope;margin:22px 0 5px">Manage vehicles</h3><div class="account-list">${vehiclesCache.map(v=>`<div class="account-item"><span>${escapeHtml(v.name)} · ₹${v.price}/day</span><button class="btn btn-outline" onclick="removeVehicle(${v.id})">Remove</button></div>`).join('')}</div>`;
   $('addVehicle').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));try{await api('/api/admin/vehicles',{method:'POST',body:JSON.stringify(d)});toast('Vehicle added successfully.');await loadVehicles();loadAccountTab('admin')}catch(err){toast(err.message)}};
  }
 }catch(e){box.innerHTML=`<div class="empty">${escapeHtml(e.message)}</div>`}
}
async function cancelBooking(id){try{await api(`/api/admin/bookings/${id}/cancel`,{method:'POST'});toast('Booking cancelled.');loadAccountTab('bookings')}catch(e){toast(e.message)}}
async function removeVehicle(id){if(!confirm('Remove this vehicle from the listings?'))return;try{await api(`/api/admin/vehicles/${id}`,{method:'DELETE'});toast('Vehicle removed.');await loadVehicles();loadAccountTab('admin')}catch(e){toast(e.message)}}
$('loginBtn').onclick=()=>authModal('login');$('signupBtn').onclick=()=>authModal('signup');$('ctaSignup').onclick=()=>currentUser?account():authModal('signup');$('dashboardBtn').onclick=account;$('closeModal').onclick=closeModal;$('modal').onclick=e=>{if(e.target===$('modal'))closeModal()};$('logoutBtn').onclick=async()=>{await api('/api/logout',{method:'POST'});currentUser=null;updateHeader();toast('You have logged out.');loadVehicles()};$('searchInput').oninput=loadVehicles;$('categoryFilter').onchange=loadVehicles;
(async()=>{await loadUser();await loadVehicles()})();
