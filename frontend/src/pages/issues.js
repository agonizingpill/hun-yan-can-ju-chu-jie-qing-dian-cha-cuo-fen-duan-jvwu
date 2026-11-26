import {el} from '../dom.js';
import {room} from '../banquet-api.js';
import {category,desk,issueState,segments} from '../custody-state.js';
import {action,body,input,picker} from '../forms.js';
import {status,titleBlock} from '../widgets.js';
import {pill} from '../components/pill.js';

export async function issues(root,role) {
  const queue=el('section',{class:'ledger'});
  const panel=el('section',{class:'action'});
  async function load(message) {
    const [issues,data,frames]=await Promise.all([room.issues(),room.layout(),room.counts()]);
    const active=issues.find(item=>item.code===desk.issue)||issues[0];
    queue.replaceChildren(el('h2',{},'箱码差错簿'),...issues.map(issue=>el('div',{class:'tray'},
      el('button',{type:'button',class:'quiet',onclick:()=>{desk.issue=issue.code;draw(issue);}},issue.code),
      ' '+category[issue.category]+' · ',pill(issueState,issue.state))));
    if(!issues.length) queue.append(status('当前没有跨台撞码或差额锁箱。'));
    draw(active,message);
    function draw(issue,note) {
      panel.replaceChildren(el('h2',{},'核对并移交责任'),note?status(note,'ok'):null);
      if(!issue) {panel.append(status('请选择一条报警。'));return;}
      const line=data.placements.find(row=>row.code===issue.placement_code);
      const frame=frames.find(row=>row.code===issue.frame_code);
      panel.append(el('p',{class:'callout'},issue.case_code+' · 原归属 '+line.table_code
        +(issue.conflicting_table ? ' · 撞码 '+issue.conflicting_table : ' · 缺 '+frame.missing+' 件')),
        pill(issueState,issue.state));
      if(issue.responsible_name) panel.append(el('p',{},segments[issue.responsible_segment]+' · '+issue.responsible_name));
      if(role!=='reviewer'||issue.state==='resolved') return;
      if(issue.category==='count_loss'&&issue.state==='open') {
        panel.append(action('assign',[
          picker('segment','责任交接段',Object.entries(segments).filter(([key])=>key!=='balanced'),frame.model_segment),
          input('person','当班责任人',{placeholder:'何师傅'}),
        ],'确认归责',async values=>{
          await room.assign(issue.code,body(values));
          desk.issue=issue.code;
          await load('已指定责任人。');
        }));
        return;
      }
      panel.append(action('resolve',[
        input('correctly_labeled_table','复核原宴台', {value:line.table_code}),
        input('witnessed_tag','实扫箱签'),
        input('counted','见证件数',{type:'number',min:'0',max:'36'}),
      ],issue.category==='count_loss'?'确认收箱结案':'恢复原台并解锁',async values=>{
        await room.resolve(issue.code,{...body(values),counted:Number(values.get('counted'))});
        desk.issue=issue.code;
        await load(issue.code+' 已结案。');
      }));
    }
  }
  root.replaceChildren(titleBlock('曼禾 · 差错交接','锁箱与责任凭证','撞码先恢复原宴台，实物差额须指定一个责任交接段并核对收箱数。'),
    el('div',{class:'split'},queue,panel));
  await load();
}
