import {el} from '../dom.js';
export function pill(names,state) {
  return el('span',{class:'pill','data-state':state},names[state] || state);
}
