export const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const money = value => `¥${Number(value||0).toLocaleString('zh-CN',{maximumFractionDigits:0})}`;
export const dateText = value => value ? String(value).replace('T',' ').slice(0,16) : '—';
export const pill = (label, tone='neutral') => `<span class="pill ${tone}">${esc(label)}</span>`;
export const metric = (value,label,detail='') => `<div class="metric"><b>${esc(value)}</b><span>${esc(label)}</span>${detail?`<small>${esc(detail)}</small>`:''}</div>`;
export function toast(message, error=false){const node=document.createElement('div');node.className=`toast ${error?'error':''}`;node.textContent=message;document.body.append(node);setTimeout(()=>node.remove(),3200);}
export function bindForm(form, handler){form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('button[type=submit]');if(button)button.disabled=true;try{await handler(Object.fromEntries(new FormData(form)))}catch(error){toast(error.message,true)}finally{if(button)button.disabled=false}})}
