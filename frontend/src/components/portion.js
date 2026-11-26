import {el} from '../dom.js';

export function portion(values) {
  return el('div',{class:'cutline','aria-label':'分段实数'},['出箱','在台','回收'].map((name,i)=>
    el('div',{},el('span',{},name),el('strong',{},values[i] == null ? '—' : String(values[i])))));
}
