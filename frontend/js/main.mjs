import { renderInputs } from './ui/inputs.mjs';
import { renderSettings } from './ui/settings.mjs';
import { renderOutput } from './ui/output.mjs';

function activate(btn){
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}

async function bootstrap(){
  const splash = document.getElementById('splash');
  const status = document.getElementById('splash-status');
  const setStatus = (msg) => {
    if(status) status.textContent = msg;
  };

  try{
    setStatus('Loading external workbook…');
    const resp = await fetch('/api/bootstrap', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: '{}'
    });

    let payload = null;
    try{
      payload = await resp.json();
    }catch(e){
      payload = null;
    }

    if(!resp.ok || !payload || payload.ok === false){
      const message = payload?.errors?.pricing || `Bootstrap failed (${resp.status})`;
      throw new Error(message);
    }

    if(payload.cache_loaded){
      const method = payload.cache_method === 'openpyxl'
        ? 'fast reader'
        : payload.cache_method === 'com'
          ? 'Excel automation'
          : 'external workbook';
      setStatus(`External workbook ready (${method}).`);
    }else if(!payload.excel_enabled){
      setStatus('Excel compatibility mode is off.');
    }else{
      setStatus('External workbook caching skipped.');
    }
  }catch(err){
    console.error('Bootstrap error', err);
    if(splash) splash.classList.add('error');
    setStatus(err?.message || 'Failed to load external workbook.');
  }finally{
    document.body.classList.remove('booting');
    await new Promise(r=>setTimeout(r, 350));
    document.body.classList.add('ready');
  }
}

async function mount(){
  await bootstrap();
  const root = document.getElementById('root');
  document.getElementById('nav-settings').addEventListener('click', async (e)=>{
    activate(e.target); await renderSettings(root);
  });
  document.getElementById('nav-inputs').addEventListener('click', async (e)=>{
    activate(e.target); await renderInputs(root);
  });
  document.getElementById('nav-generate').addEventListener('click', async (e)=>{
    activate(e.target); renderOutput(root);
  });
  await renderInputs(root);
}
window.addEventListener('DOMContentLoaded', mount);
