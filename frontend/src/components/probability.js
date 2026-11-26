import {el} from '../dom.js';
import {segments} from '../custody-state.js';
import {ratio} from '../forms.js';

export function probability(scores) {
  return el('div',{class:'votes'},Object.entries(scores).flatMap(([key,value])=>
    [el('span',{},segments[key]),el('meter',{min:'0',max:'1',value,'aria-label':segments[key]}),
      el('code',{},ratio(value))]));
}
