import {esc,pill,dateText} from './ui.js';
import {LEAD_LABELS,FOLLOWUP_LABELS} from './domain.js';
export const header = (title,subtitle,action='') => `<div class="page-head"><div><p class="eyebrow">CUSTOMER OPERATIONS / 2026-11-21</p><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p></div>${action}</div>`;
export const table = (columns, rows, empty='暂无数据') => rows.length ? `<div class="table-wrap"><table><thead><tr>${columns.map(col=>`<th>${esc(col.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(col=>`<td>${col.render?col.render(row):esc(row[col.key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : `<div class="empty">${esc(empty)}</div>`;
export const leadPill = status => pill(LEAD_LABELS[status]||status, {predicted:'blue',reviewed:'amber',queued:'green',frozen:'red',expired:'gray',rejected:'gray'}[status]||'neutral');
export const followupPill = status => pill(FOLLOWUP_LABELS[status]||status, {scheduled:'amber',contacted:'blue',declined:'red',completed:'green'}[status]||'neutral');
export const leadRow = row => `<div class="lead-card"><div><strong>${esc(row.owner_name)}</strong><span>${esc(row.vehicle_model)} · ${esc(row.plate_no)}</span></div><div class="score"><b>${Math.round(Number(row.score)*100)}%</b><span>续保概率</span></div><div>${leadPill(row.status)}</div></div>`;
export const modal = (title,body) => `<div class="modal-backdrop"><section class="modal"><div class="modal-head"><h2>${esc(title)}</h2><button class="icon-btn" data-close>×</button></div>${body}</section></div>`;
