import { apiPost } from '../api.mjs';
import { getState, setOutputs } from '../state.mjs';

export function renderOutput(root){
  const s = getState();
  root.innerHTML = `
    <div class="card">
      <h2>Generate</h2>
      <p class="muted">Creates a <span class="mono">costing.xlsx</span> and <span class="mono">quote.docx</span> using current inputs.</p>
      <div class="actions">
        <button id="go">Generate</button>
        <span id="status" class="muted"></span>
      </div>
      <div id="links"></div>
    </div>
  `;

  root.querySelector('#go').addEventListener('click', async () => {
    root.querySelector('#status').textContent = 'Working…';
    try{
      const res = await apiPost('/api/generate', {inputs: s.inputs});
      setOutputs(res.outputs);
      const links = `
        <p>Outputs:</p>
        <p><a class="btn" href="/api${res.outputs.costing_xlsx}" download>Download costing.xlsx</a>
           <a class="btn" href="/api${res.outputs.quote_docx}" download>Download quote.docx</a></p>`;
      root.querySelector('#links').innerHTML = links;
      root.querySelector('#status').textContent = 'Done ✔';
    }catch(e){
      console.error(e);
      root.querySelector('#status').textContent = 'Failed – see console.';
    }
  });
}
