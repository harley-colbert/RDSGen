import { apiGet, apiPost } from '../api.mjs';
import { getState, setInputs, setCostGrid } from '../state.mjs';

const fmtMoney = (n) =>
  (typeof n === 'number' && isFinite(n))
    ? n.toLocaleString(undefined, { style: 'currency', currency: 'USD' })
    : '—';

const fmtMs = (ms) =>
  (typeof ms === 'number' && isFinite(ms)) ? `${ms.toFixed(1)} ms` : '—';

const fmtSec = (ms) =>
  (typeof ms === 'number' && isFinite(ms)) ? `${(ms / 1000).toFixed(2)}s` : '—';

const fmtGridCell = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number' && isFinite(value)) {
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }
  if (typeof value === 'string') return value;
  return String(value ?? '');
};

const renderGridRow = (row = []) => {
  return row.map(cell => {
    const numeric = typeof cell === 'number' && isFinite(cell);
    return `<td style="padding:.25rem .5rem;border-bottom:1px solid rgba(0,0,0,0.05);border-right:1px solid rgba(0,0,0,0.05);text-align:${numeric ? 'right' : 'left'};white-space:nowrap;">${fmtGridCell(cell)}</td>`;
  }).join('');
};

function costGridHTML(grid, { loading = false, error = null } = {}) {
  if (error) {
    return `
      <div class="card" style="margin-top:1rem">
        <h3 style="margin-bottom:.5rem">Cost Grid (C4–K55)</h3>
        <div class="muted">${error}</div>
      </div>`;
  }
  if (loading) {
    return `
      <div class="card" style="margin-top:1rem">
        <div class="muted">Loading cost grid…</div>
      </div>`;
  }
  if (!Array.isArray(grid) || !grid.length) {
    return `
      <div class="card" style="margin-top:1rem">
        <h3 style="margin-bottom:.5rem">Cost Grid (C4–K55)</h3>
        <div class="muted">No cost grid data available.</div>
      </div>`;
  }

  const rows = grid.map(row => `<tr>${renderGridRow(row)}</tr>`).join('');

  return `
    <div class="card" style="margin-top:1rem">
      <h3 style="margin-bottom:.5rem">Cost Grid (C4–K55)</h3>
      <div class="muted" style="margin-bottom:.5rem">Read-only snapshot of Summary!C4:K55</div>
      <div style="max-height:18rem;overflow:auto;border:1px solid rgba(0,0,0,0.05);border-radius:.25rem;">
        <table style="width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;">
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

async function getOpts(name) {
  const res = await apiGet(`/api/options/${name}`);
  if (!res || !res.ok) return [];
  return res.values || [];
}

function selectHTML(id, values, current) {
  const opts = values.map(v => {
    const val = String(v);
    const sel = (String(current ?? '') === val) ? 'selected' : '';
    return `<option value="${val}" ${sel}>${val}</option>`;
  }).join('');
  return `<select id="${id}">${opts}</select>`;
}

function timingsHTML(meta, elapsedMs) {
  const m = meta || {};
  const rows = [];

  // Known step names (render only if present)
  const order = [
    ['t_excel_open_ms',  'Excel launch'],
    ['t_wb_open_ms',     'Workbook open'],
    ['t_wb_open_rw_ms',  'Workbook open (RW)'],
    ['t_wb_open_ro_ms',  'Workbook open (RO)'],
    ['t_write_ms',       'Write inputs'],
    ['t_calc_ms',        'Excel calculate'],
    ['t_read_ms',        'Read cells'],
    ['t_total_ms',       'Total in engine'],
  ];
  for (const [key, label] of order) {
    if (typeof m[key] === 'number') rows.push([label, fmtMs(m[key])]);
  }

  // HTTP round-trip (client observed)
  rows.push(['HTTP round-trip', fmtSec(elapsedMs)]);

  // Flags/context
  const flags = [];
  if (m.opened_readonly !== undefined) flags.push(['Opened read-only', String(!!m.opened_readonly)]);
  if (m.source) flags.push(['Source', m.source]);
  if (m.cache_ts) {
    const dt = new Date(m.cache_ts * 1000);
    flags.push(['Cache time', dt.toLocaleString()]);
  }

  const body = rows.map(([k, v]) => `
    <tr>
      <td style="padding:.25rem 0">${k}</td>
      <td style="padding:.25rem 0;text-align:right" class="muted">${v}</td>
    </tr>`).join('');

  const flagsBody = flags.map(([k, v]) => `
    <tr>
      <td style="padding:.25rem 0">${k}</td>
      <td style="padding:.25rem 0;text-align:right" class="muted">${v}</td>
    </tr>`).join('');

  const cacheNote = (m.source === 'cache_ro' && rows.length <= 1) // only HTTP present
    ? `<div class="muted" style="margin-top:.25rem">
         Served from cached costs (no Excel call this request).
       </div>`
    : '';

  return `
    <div style="margin-top:.75rem">
      <div class="muted" style="margin-bottom:.25rem">Performance</div>
      <table style="width:100%;border-collapse:collapse">
        <tbody>${body}</tbody>
      </table>
      ${flags.length ? `
        <table style="width:100%;border-collapse:collapse;margin-top:.25rem">
          <tbody>${flagsBody}</tbody>
        </table>` : ''}
      ${cacheNote}
    </div>`;
}

function pricingTableHTML(p, elapsedMs) {
  const items = p.items || {};
  const lines = [];
  lines.push({ label: 'Base System', qty: '', amount: p.base?.sell ?? 0 });

  for (const key of Object.keys(items)) {
    const it = items[key];
    if (!it || !it.qty) continue;
    lines.push({ label: it.label, qty: `× ${it.qty}`, amount: (it.sell || 0) * it.qty });
  }
  const total = lines.reduce((a, r) => a + (r.amount || 0), 0);

  return `
    <div class="card" style="margin-top:1rem">
      <h3 style="margin-bottom:.5rem">Live Pricing</h3>
      <div class="muted" style="margin-bottom:.75rem">
        Calculated from the Costing workbook at margin ${Math.round((p.margin || 0) * 100)}%
        • Completed in ${fmtSec(elapsedMs)}
      </div>
      <table style="width:100%;border-collapse:collapse">
        <tbody>
          ${lines.map(r => `
            <tr>
              <td style="padding:.35rem 0">${r.label} <span class="muted">${r.qty}</span></td>
              <td style="padding:.35rem 0;text-align:right">${fmtMoney(r.amount)}</td>
            </tr>`).join('')}
          <tr><td colspan="2"><hr></td></tr>
          <tr>
            <td style="padding:.45rem 0"><b>Total (est.)</b></td>
            <td style="padding:.45rem 0;text-align:right"><b>${fmtMoney(total)}</b></td>
          </tr>
        </tbody>
      </table>
      ${timingsHTML(p.meta, elapsedMs)}
    </div>`;
}

let priceTimer = null;
let ticker = null;

async function refreshPrice(root) {
  const target = root.querySelector('#live-pricing');
  const gridTarget = root.querySelector('#cost-grid');
  if (!target) return;

  // live stopwatch while calculating
  let start = performance.now();
  clearInterval(ticker);
  target.innerHTML = `
    <div class="card" style="margin-top:1rem">
      <div class="muted"><span id="calc-timer">Calculating… 0.00s</span></div>
    </div>`;
  const labelEl = () => target.querySelector('#calc-timer');
  ticker = setInterval(() => {
    const seconds = (performance.now() - start) / 1000;
    const el = labelEl();
    if (el) el.textContent = `Calculating… ${seconds.toFixed(2)}s`;
  }, 100);

  if (gridTarget) {
    gridTarget.innerHTML = costGridHTML([], { loading: true });
  }

  clearTimeout(priceTimer);
  priceTimer = setTimeout(async () => {
    try {
      const s = getState();
      const t0 = performance.now();

      console.time('🧮 /api/price');
      const resp = await apiPost('/api/price', { inputs: s.inputs });
      console.timeEnd('🧮 /api/price');

      const elapsed = performance.now() - t0;

      clearInterval(ticker);
      if (resp?.ok && resp.pricing) {
        // Dump whatever meta server sends (Excel step times if present)
        if (resp.pricing.meta) {
          try { console.table(resp.pricing.meta); }
          catch { console.debug('pricing meta', resp.pricing.meta); }
        }
        target.innerHTML = pricingTableHTML(resp.pricing, elapsed);
        const grid = resp.pricing.grid || [];
        setCostGrid(grid);
        if (gridTarget) {
          gridTarget.innerHTML = costGridHTML(grid);
        }
      } else {
        target.innerHTML = `
          <div class="card" style="margin-top:1rem"><div class="muted">
            No pricing available. Check Excel compat settings and workbook path in Settings.
          </div></div>`;
        if (gridTarget) {
          gridTarget.innerHTML = costGridHTML([], { error: 'No cost grid data available.' });
        }
      }
    } catch (e) {
      clearInterval(ticker);
      target.innerHTML = `
        <div class="card" style="margin-top:1rem"><div class="muted">
          Pricing error: ${e?.message || e}. See Network → /api/price.
        </div></div>`;
      if (gridTarget) {
        gridTarget.innerHTML = costGridHTML([], { error: 'Failed to load cost grid.' });
      }
    }
  }, 250); // debounce rapid changes
}

export async function renderInputs(root) {
  const s = getState();
  const inp = s.inputs || {};

  // Load dropdown values from backend so UI matches workbook
  const [
    sparePartsVals,
    spareBladesVals,
    sparePadsVals,
    guardingVals,
    feedingVals,
    transformerVals,
    trainingVals,
  ] = await Promise.all([
    getOpts('spare_parts_qty'),
    getOpts('spare_blades_qty'),
    getOpts('spare_pads_qty'),
    getOpts('guarding'),
    getOpts('feeding'),
    getOpts('transformer'),
    getOpts('training'),
  ]);

  root.innerHTML = `
    <div class="card">
      <h2>Inputs</h2>
      <div class="muted">These controls mirror the workbook's System Options.</div>

      <label>Margin (decimal 0–0.99)</label>
      <input id="margin" type="number" step="0.01" min="0" max="0.99" value="${inp.margin ?? 0.24}" />

      <hr>

      <label>Spare Parts Package (qty)</label>
      ${selectHTML('spare_parts_qty', sparePartsVals, inp.spare_parts_qty ?? 0)}

      <label>Spare Saw Blades (qty)</label>
      ${selectHTML('spare_blades_qty', spareBladesVals, inp.spare_blades_qty ?? 0)}

      <label>Spare Foam Pads (qty)</label>
      ${selectHTML('spare_pads_qty', sparePadsVals, inp.spare_pads_qty ?? 0)}

      <label>Guarding</label>
      ${selectHTML('guarding', guardingVals, inp.guarding ?? 'Standard')}

      <label>Feeding</label>
      ${selectHTML('feeding', feedingVals, inp.feeding ?? 'No')}

      <label>Transformer</label>
      ${selectHTML('transformer', transformerVals, inp.transformer ?? 'None')}

      <label>Training</label>
      ${selectHTML('training', trainingVals, inp.training ?? 'English')}

      <div class="actions" style="margin-top:.75rem">
        <button id="save">Save</button>
      </div>
    </div>

    <div id="live-pricing"></div>
    <div id="cost-grid"></div>
  `;

  // No-op placeholder; keep your own validation/save if you have it
  root.querySelector('#save').addEventListener('click', () => {});

  const onChange = (e) => {
    const el = e.target;
    let v = el.value;

    // Guard the margin field so we don't POST invalid numbers while typing
    if (el.id === 'margin') {
      const raw = el.value;
      // empty, "-", ".", or not a number => wait until valid
      if (raw === '' || raw === '-' || raw === '.' || Number.isNaN(Number(raw))) {
        setInputs({ margin: raw }); // keep local state but don't recompute yet
        return;                     // avoid 500s from the backend
      }
      v = Number(raw);
      // clamp just in case
      if (v < 0) v = 0;
      if (v >= 0.9999) v = 0.9999;
    } else if (['spare_parts_qty','spare_blades_qty','spare_pads_qty'].includes(el.id)) {
      v = Number(v);
    }

    setInputs({ [el.id]: v });
    refreshPrice(root);
  };

  root.querySelectorAll('input,select').forEach(el => {
    el.addEventListener('input', onChange);
    el.addEventListener('change', onChange);
  });

  const gridTarget = root.querySelector('#cost-grid');
  if (gridTarget) {
    const existing = Array.isArray(s.costGrid) ? s.costGrid : [];
    gridTarget.innerHTML = costGridHTML(existing);
  }

  // Initial pricing
  refreshPrice(root);
}
