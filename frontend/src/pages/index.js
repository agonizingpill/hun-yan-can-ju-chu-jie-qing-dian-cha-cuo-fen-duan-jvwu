import {floor} from './floor.js';
import {counts} from './counts.js';
import {issues} from './issues.js';
import {close} from './close.js';

export const info={title:'曼禾宴台盖箱',customer:'曼禾餐具工场 · 婚宴出借组',
  purpose:'按原宴台归属查出借和回收，给每张异常清点单保留交接依据。'};
export const pages=[
  {key:'floor',title:'布席与盖箱',render:floor}, {key:'counts',title:'分段清点',render:counts},
  {key:'issues',title:'锁箱与归责',render:issues}, {key:'close',title:'撤席签收',render:close},
];
