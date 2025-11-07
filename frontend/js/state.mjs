const state = {
  settings: null,
  inputs: {
    margin: 0.24,
    base_price: 414320.82,
    spare_parts_qty: 1,
    spare_blades_qty: 0,
    spare_pads_qty: 0,
    guarding: 'Standard',
    feeding: 'No',
    transformer: 'None',
    training: 'English'
  },
  outputs: null,
  costGrid: []
};

export function getState(){ return state; }
export function setSettings(s){ state.settings = s; }
export function setInputs(i){ state.inputs = {...state.inputs, ...i}; }
export function setOutputs(o){ state.outputs = o; }
export function setCostGrid(grid){
  if (!Array.isArray(grid)) {
    state.costGrid = [];
    return;
  }
  state.costGrid = grid.map(row => Array.isArray(row) ? [...row] : []);
}
