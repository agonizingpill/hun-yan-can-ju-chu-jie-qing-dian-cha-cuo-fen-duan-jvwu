import {awaitCompute,request} from './api.js';
export const room = {
  layout:()=>request('/room'), place:body=>request('/room/placement',body),
  clear:code=>request('/room/'+code+'/clear',{}),
  counts:()=>request('/counts'), activeModel:()=>request('/counts/active-model'),
  proposal:body=>request('/counts/review',body),
  result:awaitCompute, sign:body=>request('/counts/sign',body),
  issues:()=>request('/custody'), assign:(code,body)=>request('/custody/'+code+'/assign',body),
  resolve:(code,body)=>request('/custody/'+code+'/resolve',body),
  revise:(code,body)=>request('/custody/'+code+'/revise',body),
};
export const models = {
  overview:()=>request('/models'),
  train:()=>request('/models/train',{}),
  promote:version=>request('/models/'+version+'/promote',{}),
  demoDataset:()=>request('/models/demo-dataset',{}),
};
