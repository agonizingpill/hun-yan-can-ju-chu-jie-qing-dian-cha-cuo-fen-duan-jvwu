import {el} from '../dom.js';
import {models,room} from '../banquet-api.js';
import {modelState,segments} from '../custody-state.js';
import {action,input,picker} from '../forms.js';
import {status,titleBlock} from '../widgets.js';
import {pill} from '../components/pill.js';

export async function modelsPage(root,role) {
  const ledger=el('section',{class:'ledger'});
  const panel=el('section',{class:'action'});
  const reviewer=role==='reviewer';

  async function load(message) {
    const [overview,issues,frames]=await Promise.all([models.overview(),room.issues(),room.counts()]);
    ledger.replaceChildren(
      el('h2',{},'分段模型版本'),
      el('p',{class:'callout mono'},'当前给新单使用：'+overview.active_version),
      ...overview.versions.map(version=>el('article',{class:'record'},
        el('h3',{},version.code),
        pill(modelState,version.status),
        el('dl',{},
          el('dt',{},'训练箱数'),el('dd',{},String((version.trained_on_cases||[]).length)),
          el('dt',{},'每段样本'),el('dd',{},JSON.stringify(version.metrics?.per_segment||{})),
          el('dt',{},'过期归责箱'),el('dd',{},(version.stale_label_cases||[]).join('、')||'无'),
          el('dt',{},'训练时间'),el('dd',{},version.trained_at||''))),
      el('h2',{},'过关评审记录'),
      overview.campaigns.length
        ? el('div',{class:'records'},overview.campaigns.map(c=>el('article',{class:'record'},
            el('h3',{},c.code),el('p',{},c.candidate_version+' 对 '+c.incumbent_version),
            el('p',{},c.decision+(c.reason?' · '+c.reason:'')))))
        :status('暂无评审记录。候选与在用版在同一批评审验收箱上逐段比漏判。')));

    panel.replaceChildren(el('h2',{},'训练与上线治理'),message?status(message,'ok'):null);
    if(!reviewer) {
      panel.append(status('仅复核员可训练候选、评审切换与更正结案归责。'));
      return;
    }
    const candidates=overview.versions.filter(v=>v.status==='training'||v.status==='evaluated');
    panel.append(
      action('train-model',[],'用已结案人工归责训练候选版',async ()=>{
        const report=await models.train();
        await load('候选 '+report.version+' 已训练，训练 '+report.train_cases
          +' 箱、验收 '+report.validation_cases+' 箱（婚宴 '+report.validation_parties.join('、')+'）。');
      }),
      candidates.length
        ? action('promote-model',[
            picker('version','参评候选',candidates.map(v=>[v.code,v.code]))],
            '同一批评审箱对比并切换',async form=>{
              const report=await models.promote(form.get('version'));
              await load(report.decision==='promoted'
                ? '已一次性切换到 '+form.get('version')+'：'+report.reason
                : '未换版：'+report.reason);
            })
        : status('没有待评审候选，先训练。'));

    // 已结案缺件差错可更正归责；更正后用过旧归责的版本作废并回退。
    const revisable=issues.filter(i=>i.category==='count_loss'&&i.state==='resolved');
    if(revisable.length) {
      const frameOf=code=>frames.find(f=>f.code===code);
      panel.append(el('h3',{},'更正结案归责（触发版本作废与回退）'),
        ...revisable.map(issue=>{
          const frame=frameOf(issue.frame_code);
          return el('details',{class:'ticket'},
            el('summary',{},issue.case_code+' · 现归责 '+(segments[issue.responsible_segment]||issue.responsible_segment)),
            action('revise-'+issue.code,[
              picker('segment','更正责任段',
                Object.entries(segments).filter(([key])=>key!=='balanced'),issue.responsible_segment),
              input('person','更正责任人',{value:issue.responsible_name||''})],
              '更正归责并作废相关版本',async form=>{
                const result=await room.revise(issue.code,{
                  segment:form.get('segment'),person:form.get('person')});
                await load(issue.case_code+' 已更正；作废版本 '
                  +(result.invalidated_versions.join('、')||'无')
                  +'；在用版回退到 '+(result.active_version||'保持不变'));
              }));
        }));
    }
  }

  root.replaceChildren(titleBlock('曼禾 · 模型治理','分段模型版本与过关',
      '只用已结案人工归责训练；同场婚宴的箱不跨训练与验收；三段缺件都要有样本，任一段漏判更多即不换版；过关一次性切换，排队清点按领号版本算。'),
    el('div',{class:'split'},ledger,panel));
  await load();
}
