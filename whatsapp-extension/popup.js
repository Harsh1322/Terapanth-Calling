const status = document.getElementById('status');
let contacts = [];
document.getElementById('scan').onclick = async () => {
  const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
  if (!tab || !tab.url || !tab.url.startsWith('https://web.whatsapp.com/')) { status.textContent='Open WhatsApp Web first.'; return; }
  chrome.tabs.sendMessage(tab.id, {type:'SCAN_VISIBLE_PARTICIPANTS'}, result => {
    if (chrome.runtime.lastError) { status.textContent='Refresh WhatsApp Web, open the group participant list, then try again.'; return; }
    contacts = (result && result.contacts) || [];
    status.textContent = `Found ${contacts.length} visible candidate(s). Download CSV or send to tracker after review.`;
  });
};
document.getElementById('download').onclick = () => {
  if (!contacts.length) { status.textContent='Scan first.'; return; }
  const esc = x => '"' + String(x||'').replace(/"/g,'""') + '"';
  const csv = 'name,phone,group\n' + contacts.map(c => [c.name,c.phone,c.group].map(esc).join(',')).join('\n');
  const url = URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  chrome.downloads ? chrome.downloads.download({url,filename:'whatsapp_group_contacts.csv',saveAs:true}) : (()=>{const a=document.createElement('a');a.href=url;a.download='whatsapp_group_contacts.csv';a.click();})();
  status.textContent='CSV prepared. Import it through the tracker dashboard.';
};
document.getElementById('send').onclick = async () => {
  if (!contacts.length) { status.textContent='Scan first.'; return; }
  const api = prompt('Paste your tracker URL (for example https://your-app.onrender.com):');
  if (!api) return;
  const token = prompt('Paste your signed-in Django session cookie is not supported here. For safety, use CSV import from the admin dashboard instead. Cancel this flow and choose Download CSV.');
  status.textContent='Direct sending is disabled. Download the CSV and import it from the signed-in admin dashboard.';
};
