function visible(el) {
  const r = el.getBoundingClientRect(), s = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
}
function phoneFromText(text) {
  const match = String(text||'').match(/(?:\+?\d[\d\s().-]{7,}\d)/);
  if (!match) return '';
  const digits = match[0].replace(/\D/g,'');
  if (digits.length < 8 || digits.length > 15) return '';
  return match[0].trim();
}
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type !== 'SCAN_VISIBLE_PARTICIPANTS') return;
  const candidates = [...document.querySelectorAll('[role="listitem"], [data-testid*="cell-frame"], span[title], div[title]')].filter(visible);
  const seen = new Set(), contacts = [];
  for (const el of candidates) {
    const text = (el.innerText || el.getAttribute('title') || '').trim();
    const title = (el.getAttribute('title') || '').trim();
    const phone = phoneFromText(title) || phoneFromText(text);
    if (!phone) continue;
    const key = phone.replace(/\D/g,'');
    if (seen.has(key)) continue;
    seen.add(key);
    const name = title && !phoneFromText(title) ? title : text.replace(phone,'').trim().split('\n')[0];
    const detectedGroup = document.title.replace(/\s*-\s*WhatsApp.*$/i,'').trim();
    contacts.push({name: name.slice(0,180), phone, group: (msg.groupName || detectedGroup).slice(0,180)});
  }
  sendResponse({contacts});
  return true;
});
