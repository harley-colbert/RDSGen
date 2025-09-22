
import { apiGet, apiPost } from '../api.mjs';
import { getState, setSettings } from '../state.mjs';

async function browse(field, mode, title, filters){
  const params = new URLSearchParams({ mode, title });
  if (filters) params.set('filters', filters);
  const r = await apiGet('/api/browse?' + params.toString());
  if (r && r.ok && r.path){
    const input = document.getElementById(field);
    if (input) input.value = r.path;
  }
}

export async function renderSettings(root){
  const resp = await apiGet('/api/settings');
  setSettings(resp);
  const s = getState().settings;

  root.innerHTML = `
    <div class="card">
      <h2>Settings</h2>
      <div class="row">
        <label>Output Directory</label>
        <div style="display:flex;gap:.5rem;align-items:center">
          <input id="OUTPUT_DIR" value="${s.OUTPUT_DIR||''}" style="flex:1">
          <button class="btn browse" data-for="OUTPUT_DIR" data-mode="open_dir">Browse…</button>
        </div>
      </div>
      <div class="row">
        <label>Word Template</label>
        <div style="display:flex;gap:.5rem;align-items:center">
          <input id="WORD_TEMPLATE_PATH" value="${s.WORD_TEMPLATE_PATH||''}" style="flex:1">
          <button class="btn browse" data-for="WORD_TEMPLATE_PATH" data-mode="open_file" data-filters="Word files|*.docx;All files|*.*">Browse…</button>
        </div>
      </div>
      <div class="row">
        <label>Costing Template</label>
        <div style="display:flex;gap:.5rem;align-items:center">
          <input id="COSTING_TEMPLATE_PATH" value="${s.COSTING_TEMPLATE_PATH||''}" style="flex:1">
          <button class="btn browse" data-for="COSTING_TEMPLATE_PATH" data-mode="open_file" data-filters="Excel files|*.xlsx;Excel binary|*.xlsb;All files|*.*">Browse…</button>
        </div>
      </div>
      <div class="row">
        <label>External Workbook</label>
        <div style="display:flex;gap:.5rem;align-items:center">
          <input id="EXTERNAL_WORKBOOK_PATH" value="${s.EXTERNAL_WORKBOOK_PATH||''}" style="flex:1">
          <button class="btn browse" data-for="EXTERNAL_WORKBOOK_PATH" data-mode="open_file" data-filters="Excel files|*.xlsx;Excel binary|*.xlsb;All files|*.*">Browse…</button>
        </div>
      </div>
      <div class="row">
        <label>Excel Compat Mode</label>
        <select id="EXCEL_COMPAT_MODE">
          <option value="false">Off</option>
          <option value="true">On</option>
        </select>
      </div>
      <div class="actions">
        <button id="save">Save</button>
        <span id="status" class="muted"></span>
      </div>
    </div>
  `;
  root.querySelector('#EXCEL_COMPAT_MODE').value = String(!!s.EXCEL_COMPAT_MODE);

  root.querySelectorAll('.browse').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const el = e.currentTarget;
      const field = el.getAttribute('data-for');
      const mode = el.getAttribute('data-mode') || 'open_file';
      const filters = el.getAttribute('data-filters') || '';
      const title = 'Select ' + field.replace(/_/g,' ').toLowerCase();
      try{
        await browse(field, mode, title, filters);
      }catch(err){
        console.error('browse failed', err);
      }
    });
  });

  root.querySelector('#save').addEventListener('click', async () => {
    const data = {
      OUTPUT_DIR: document.getElementById('OUTPUT_DIR').value.trim(),
      WORD_TEMPLATE_PATH: document.getElementById('WORD_TEMPLATE_PATH').value.trim(),
      COSTING_TEMPLATE_PATH: document.getElementById('COSTING_TEMPLATE_PATH').value.trim(),
      EXTERNAL_WORKBOOK_PATH: document.getElementById('EXTERNAL_WORKBOOK_PATH').value.trim(),
      EXCEL_COMPAT_MODE: document.getElementById('EXCEL_COMPAT_MODE').value === 'true',
    };
    try{
      const res = await apiPost('/api/settings', data);
      setSettings(res.settings);
      document.getElementById('status').textContent = 'Saved ✔';
    }catch(e){
      console.error(e);
      document.getElementById('status').textContent = 'Save failed – check paths.';
    }
  });
}
