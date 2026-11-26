import {el} from './dom.js';
import {status} from './widgets.js';

export const mayWrite=role=>role==='operator'||role==='reviewer';
export const ratio=value=>(value*100).toFixed(1)+'%';
export const body=fields=>Object.fromEntries(fields);

export function input(name,label,props={}) {
  return el('label',{},el('span',{},label),el('input',{name,required:'',...props}));
}

export function picker(name,label,options,selected) {
  return el('label',{},el('span',{},label),el('select',{name,required:''},options.map(([value,text])=>
    el('option',{value,selected:value===selected?'':undefined},text))));
}

export function action(id,children,label,submit) {
  const notice=status('');
  const button=el('button',{type:'submit'},label);
  const form=el('form',{id},children,button,notice);
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    notice.textContent='';
    button.disabled=true;
    try {
      const message=await submit(new FormData(form));
      notice.textContent=message || '';
      notice.className='status ok';
    } catch(error) {
      notice.textContent=error.message;
      notice.className='status error';
    } finally {button.disabled=false;}
  });
  return form;
}
