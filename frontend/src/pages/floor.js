import {el} from '../dom.js';
import {room} from '../banquet-api.js';
import {caseState,desk,tableState} from '../custody-state.js';
import {action,body,input,mayWrite,picker} from '../forms.js';
import {status,titleBlock} from '../widgets.js';
import {pill} from '../components/pill.js';

export async function floor(root,role) {
  const map=el('div',{class:'floor'});
  const tray=el('div',{});
  const check=el('section',{class:'action'});
  async function load(message) {
    const data=await room.layout();
    map.replaceChildren(...data.tables.map(table=>{
      const linked=data.placements.filter(item=>item.table_code===table.code);
      return el('article',{class:'table-seat'},el('i',{},String(table.seats)),
        el('div',{},el('h3',{},table.code+' · '+table.hall),el('p',{},table.party+' / '+table.course+' / '+table.runner)),
        el('div',{},pill(tableState,table.state),el('p',{},linked.length+' 箱')));
    }));
    tray.replaceChildren(...data.cases.map(item=>{
      const placed=data.placements.find(line=>line.case_code===item.code);
      return el('div',{class:'tray'},el('code',{},item.code+' · '),el('strong',{},item.dish+' · '),pill(caseState,item.state),
        el('p',{},'封签 '+item.lid_tag+' · 整箱应有 '+item.capacity+' 件 · '+(placed ? placed.table_code:'未分台')));
    }));
    check.replaceChildren(el('h2',{},'签发宴台唯一交接'),message?status(message,'ok'):null);
    if(!mayWrite(role)) {check.append(status('只读过目宴台和封盖箱。'));return;}
    check.append(action('place',[
      input('code','交接编号',{placeholder:'P-1124-A08'}),
      picker('table_code','宴台',data.tables.filter(table=>table.state==='arranged').map(table=>[table.code,table.code+' · '+table.hall]),'MH-A08'),
      picker('case_code','箱码',data.cases.map(item=>[item.code,item.code+' · '+item.dish])),
      input('lid_tag','实扫箱盖签',{placeholder:'LID-R08'}),
      input('outbound_count','离后台件数',{type:'number',min:'0',max:'36',value:'12'}),
    ],'签收盖箱',async form=>{
      const result=await room.place({...body(form),outbound_count:Number(form.get('outbound_count'))});
      if(result.issue_code) {
        desk.issue=result.issue_code;
        await load(result.scanned_table+' 与 '+result.expected_table+' 撞码，已锁箱。');
      } else {
        desk.placement=result.placement.code;
        await load(result.placement.code+' 已签收盖箱。');
      }
    }));
  }
  root.replaceChildren(titleBlock('曼禾 · 宴台布席','席位与盖箱交接','箱码只保留一次实际宴台归属。发现跨宴台重复扫描，原归属留存，箱进入差错锁定。'),
    el('div',{class:'split'},el('section',{class:'ledger'},el('h2',{},'厅面席位'),map,el('h2',{},'盖箱簿'),tray),check));
  await load();
}
