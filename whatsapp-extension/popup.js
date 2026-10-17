const status = document.getElementById('status');
let contacts = [];
const groupName = document.getElementById('group-name');

chrome.storage.local.get(['groupName'], data => { groupName.value = data.groupName || ''; });
document.getElementById('open-whatsapp').onclick = () => {
  chrome.tabs.create({url: 'https://web.whatsapp.com/'});
  status.textContent = 'Sign in to WhatsApp Web, open the target group participant list, then return here to scan.';
};
document.getElementById('scan').onclick = async () => {
  const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
  if (!tab || !tab.url || !tab.url.startsWith('https://web.whatsapp.com/')) { status.textContent='Open WhatsApp Web first.'; return; }
  const requestedGroup = groupName.value.trim();
  chrome.storage.local.set({groupName: requestedGroup});
  chrome.tabs.sendMessage(tab.id, {type:'SCAN_VISIBLE_PARTICIPANTS', groupName: requestedGroup}, result => {
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
