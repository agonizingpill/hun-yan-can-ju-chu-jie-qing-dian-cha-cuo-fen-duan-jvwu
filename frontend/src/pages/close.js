import {el} from '../dom.js';
import {room} from '../banquet-api.js';
import {caseState,tableState} from '../custody-state.js';
import {action} from '../forms.js';
import {status,titleBlock} from '../widgets.js';
import {pill} from '../components/pill.js';

export async function close(root,role) {
  const sections=el('div',{class:'floor'});
  async function load(message) {
    const data=await room.layout();
    sections.replaceChildren(message?status(message,'ok'):null,...data.tables.map(table=>{
      const assigned=data.placements.filter(line=>line.table_code===table.code)
        .map(line=>data.cases.find(item=>item.code===line.case_code));
      const waiting=assigned.filter(item=>item.state!=='closed').length;
      const card=el('section',{class:'action'},el('h2',{},table.code+' · '+table.hall),pill(tableState,table.state),
        el('p',{},table.party+' · '+table.runner),el('p',{},assigned.length+' 箱交接 · '+waiting+' 箱仍待处理'),
        ...assigned.map(item=>el('p',{class:'tray'},item.code+' ',pill(caseState,item.state))));
      if(role==='reviewer'&&table.state==='arranged'&&assigned.length) {
        card.append(action('clear-'+table.code,[],'签撤席',async ()=>{
          await room.clear(table.code);
          await load(table.code+' 已签撤席。');
        }));
      }
      return card;
    }).filter(Boolean));
  }
  root.replaceChildren(titleBlock('曼禾 · 撤席签收','宴台收场单','清点和差错交接完成后，复核员确认撤席。'),
    sections);
  await load();
}
