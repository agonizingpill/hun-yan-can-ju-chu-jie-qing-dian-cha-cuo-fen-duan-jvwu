import {el} from '../dom.js';
import {room} from '../banquet-api.js';
import {desk,fields,segments} from '../custody-state.js';
import {action,input,mayWrite,picker} from '../forms.js';
import {status,titleBlock} from '../widgets.js';
import {pill} from '../components/pill.js';
import {portion} from '../components/portion.js';
import {probability} from '../components/probability.js';

export async function counts(root,role) {
  const entry=el('section',{class:'action'});
  const statement=el('section',{class:'ledger'});
  async function load(message) {
    const [layout,records,active]=await Promise.all([room.layout(),room.counts(),room.activeModel()]);
    const assignments=layout.placements.filter(line=>layout.cases.find(item=>item.code===line.case_code)?.state==='at_table');
    const output=el('div',{class:'result'});
    entry.replaceChildren(el('h2',{},'计数证据'),message?status(message,'ok'):null);
    statement.replaceChildren(
      el('h2',{},'分段判别与清点单'),
      el('p',{class:'callout mono'},'当前给新单使用的模型版本：'+active.active_version
        +'（已排队的清点按领号时钉住的版本算）'),
      output,
      records.length ? records.map(item=>{
        const link=layout.placements.find(line=>line.code===item.placement_code);
        return el('details',{class:'ticket'},el('summary',{},item.code+' · '+(link?.case_code || item.placement_code)
          +' · '+item.missing+' 缺件'),portion([link?.outbound_count,item.table_count,item.return_count]),
          pill(segments,item.model_segment),probability(item.votes),
          el('p',{class:'mono'},'领号版本：'+(item.model_version || '未记录')));
      }):status('清点签入后显示现场读数和票比。'));
    if(!mayWrite(role)||!assignments.length) {
      entry.append(status('可清点的箱须先签收且没有差错锁。'));
      return;
    }
    entry.append(action('count-frame',[
      picker('placement_code','宴台箱交接',assignments.map(line=>[line.code,line.code+' / '+line.case_code]),desk.placement),
      el('div',{class:'fields'},input('table_count','席间实数',{type:'number',min:'0',max:'36',value:'8'}),
        input('return_count','回收实数',{type:'number',min:'0',max:'36',value:'7'})),
      el('div',{class:'fields'},Object.entries(fields).map(([name,label])=>input(name,label,
        {type:'number',min:'0',max:'1',step:'.01',value:'.2'}))),
    ],'复核分段',async form=>{
      const selected=assignments.find(line=>line.code===form.get('placement_code'));
      const numbers=Object.fromEntries(['table_count','return_count',...Object.keys(fields)].map(name=>[name,Number(form.get(name))]));
      const queued=await room.proposal({placement_code:selected.code,...numbers});
      const review=await room.result(queued.token,item=>{
        if(item.status==='queued') output.replaceChildren(status('等候分段判别'));
      });
      if(review.status!=='ready') throw new Error(review.detail);
      const prediction=review.result;
      output.replaceChildren(el('h3',{},'分段票比'),portion([selected.outbound_count,numbers.table_count,numbers.return_count]),
        pill(segments,prediction.model_segment),probability(prediction.votes),
        el('p',{class:'mono'},prediction.model+' · 留出 '+prediction.holdout.holdout+' 条'),
        action('sign-count',[input('code','清点单号',{placeholder:'CT-1124-A08'})],'签入清点单',async values=>{
          const record=await room.sign({code:values.get('code'),token:queued.token});
          if(record.missing) desk.issue='LOSS-'+record.code.slice(0,21);
          await load(record.code+(record.missing ? ' 缺 '+record.missing+' 件，已锁箱。':' 已平衡结单。'));
        }));
    }));
  }
  root.replaceChildren(titleBlock('曼禾 · 分段清点','按出借到回收复核','记录席间和回收实数，再用影像清点特征估计可能出错的交接段。'),
    el('div',{class:'split reverse'},entry,statement));
  await load();
}
