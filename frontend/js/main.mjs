import { renderInputs } from './ui/inputs.mjs';
import { renderSettings } from './ui/settings.mjs';
import { renderOutput } from './ui/output.mjs';

function activate(btn){
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}

async function mount(){
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
