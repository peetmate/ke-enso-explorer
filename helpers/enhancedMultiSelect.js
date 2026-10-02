const se={en:{selectAll:"Select All",deselectAll:"Deselect All",noneSelected:"None selected",search:"Search\u2026",options:"Options",selected:s=>`${s} selected`},fr:{selectAll:"Tout s\xE9lectionner",deselectAll:"Tout d\xE9s\xE9lectionner",noneSelected:"Aucune s\xE9lection",search:"Rechercher\u2026",options:"Options",selected:s=>`${s} s\xE9lectionn\xE9${s===1?"":"s"}`}};export function enhancedMultiSelect(s,{maxSelections:j=null,requireAtLeastOne:D=!0,enableSelectAll:U=!1,searchable:ae=!1,compactLabelThreshold:X=null,language:le="en",labels:ie={},minWidth:q="240px",maxWidth:H="400px"}={}){s?.atlasMultiSelect?.destroy?.();const n=s?.querySelector?.("select")||s;if(!n?.matches?.("select[multiple]"))throw new TypeError("enhancedMultiSelect requires a multiple Inputs.select()");const v=Number.isFinite(j)?Math.max(0,Math.floor(j)):1/0;if(D&&v===0)throw new RangeError("maxSelections must be at least 1 when requireAtLeastOne is true");const m={...se[le]??se.en,...ie},P=new AbortController,ce=P.signal,p={wrapper:`
      font-family: inherit; width: 100%; min-width: 0; max-width: ${H};
      box-sizing: border-box; padding: 0; position: relative;
      font-size: var(--atlas-input-font-size, 13px); line-height: 1.35;
    `,btn:`
      width: 100%; height: 40px; box-sizing: border-box; padding: 8px 12px;
      background: var(--atlas-color-surface, #fff);
      border: 2px solid var(--atlas-color-border, #c9c9c9);
      border-radius: var(--atlas-radius-control, 8px);
      cursor: pointer; font-family: inherit;
      font-size: var(--atlas-input-font-size, 13px); font-weight: 400;
      line-height: 1.35;
      text-align: left; display: flex; justify-content: space-between;
      align-items: center;
      transition: var(--atlas-transition-control, border-color 200ms ease, background-color 200ms ease, color 200ms ease);
      color: var(--atlas-color-text-muted, #4a5568);
    `,list:`
      display: none; width: 100%; box-sizing: border-box;
      border: 1px solid var(--atlas-color-control-border, #d1d5db);
      border-radius: var(--atlas-radius-control, 8px);
      background: var(--atlas-color-surface, #fff);
      z-index: 10; top: 100%; position: absolute;
      overflow: hidden; padding: 0; margin-top: 4px;
      box-shadow: var(--atlas-shadow-popover, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
    `,buttonContainer:`
      display: flex; gap: 8px; padding: 8px 12px;
      border-bottom: 2px solid var(--atlas-color-divider, #e5e7eb);
      background: var(--atlas-color-surface-muted, #f9fafb);
      position: relative; z-index: 1;
    `,optionsContainer:`
      max-height: 240px; overflow-y: auto; padding: 0;
      overscroll-behavior: contain;
    `,searchContainer:`
      padding: 8px 12px;
      border-bottom: 1px solid var(--atlas-color-divider, #e5e7eb);
      background: var(--atlas-color-surface, #fff);
    `,searchInput:`
      display: block; width: 100%; box-sizing: border-box;
      padding: 7px 9px;
      border: 1px solid var(--atlas-color-control-border, #d1d5db);
      border-radius: var(--atlas-radius-action, 4px);
      background: var(--atlas-color-surface, #fff);
      color: var(--atlas-color-text, #111);
      font: inherit;
    `,actionBtn:`
      flex: 1; padding: 6px 12px;
      font-size: var(--atlas-input-action-font-size, 12px); font-weight: 500;
      border: 1px solid var(--atlas-color-control-border, #d1d5db);
      border-radius: var(--atlas-radius-action, 4px); cursor: pointer;
      background: var(--atlas-color-surface, #fff);
      transition: var(--atlas-transition-action, border-color 150ms ease, background-color 150ms ease, color 150ms ease);
    `,option:`
      padding: 8px 12px; cursor: pointer; display: flex;
      color: var(--atlas-color-text-muted, #4a5568);
      font-family: inherit; font-size: var(--atlas-input-font-size, 13px);
      font-weight: 400; line-height: 1.35;
      justify-content: space-between; align-items: center;
      border-bottom: 1px solid var(--atlas-color-divider, #e5e7eb);
      transition: background-color 100ms ease;
    `,check:`
      color: var(--atlas-color-check, rgba(0, 0, 0, 0.8));
      font-weight: 400; margin-left: 12px; min-width: 15px;
    `},b=(e,t)=>{e.style.cssText=t},i=(e,t,o,r={})=>{e.addEventListener(t,o,{...r,signal:ce})},Q=e=>String(e).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase(),A=()=>Array.from(n.options,e=>e.selected).join(","),L=()=>Array.from(n.options).filter(e=>e.selected),V=e=>{const t=e.style.backgroundColor;e.style.backgroundColor="var(--atlas-color-danger-surface, #ffe5e5)",window.setTimeout(()=>{e.style.backgroundColor=t},180),e.animate?.([{transform:"translateX(0)"},{transform:"translateX(-2px)"},{transform:"translateX(2px)"},{transform:"translateX(0)"}],{duration:200})},G=n.getAttribute("style"),J=s!==n?s.getAttribute("style"):null;n.style.display="none";const K=()=>{const e=L();if(e.length>v&&e.slice(v).forEach(t=>t.selected=!1),D&&n.selectedIndex===-1&&n.options.length){const t=Array.from(n.options).find(o=>!o.disabled)??n.options[0];t.selected=!0}};K();const u=document.createElement("div");u.className="enhanced-multiselect",b(u,p.wrapper),s!==n&&(s.style.boxSizing="border-box",s.style.flex=`1 1 ${q}`,s.style.width="100%",s.style.minWidth=`min(${q}, 100%)`,s.style.maxWidth=H);const W=`atlas-multiselect-${globalThis.crypto?.randomUUID?.()??Math.random().toString(36).slice(2)}`,a=document.createElement("button");a.type="button",a.disabled=n.disabled,a.setAttribute("aria-haspopup","listbox"),a.setAttribute("aria-expanded","false"),a.setAttribute("aria-controls",W),b(a,p.btn);const N=document.createElement("span");N.style.cssText=`
    pointer-events: none; flex: 1; min-width: 0; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
  `;const k=document.createElement("span");k.setAttribute("aria-hidden","true"),k.style.cssText="opacity: 0.7; pointer-events: none;",a.append(N,k);const f=document.createElement("div");f.className="enhanced-multiselect-list",f.hidden=!0,b(f,p.list);const x=document.createElement("div");x.id=W,x.className="enhanced-multiselect-options",x.setAttribute("role","listbox"),x.setAttribute("aria-multiselectable","true");const de=s!==n?s.querySelector("label")?.textContent?.trim():"";x.setAttribute("aria-label",de||String(m.options)),b(x,p.optionsContainer);let h=!1,C=A(),c=null,y=[],O=new AbortController,Y=!1;const B=(e,t,o)=>{e.addEventListener(t,o,{signal:O.signal})},Z=()=>y.filter(({option:e,row:t})=>!e.disabled&&!t.hidden),w=(e,{focus:t=!1}={})=>{y.forEach(({row:o})=>{o.tabIndex=o===e?.row?0:-1}),t&&e?.row.focus({preventScroll:!0})},S=(e="selected")=>{const t=Z();return t.length?e==="first"?t[0]:e==="last"?t.at(-1):t.find(({option:o})=>o.selected)??t[0]:null},T=e=>{const t=Q(e).trim();y.forEach(({row:r})=>{r.hidden=t.length>0&&!r.dataset.search.includes(t)});const o=y.find(({row:r})=>r.tabIndex===0);(!o||o.row.hidden||o.option.disabled)&&w(S("first"))};function E(){const e=L(),t=Number.isFinite(X)&&e.length>X,o=typeof m.selected=="function"?m.selected(e.length):String(m.selected).replace("{count}",e.length),r=e.length?t?String(o):e.map(d=>d.textContent).join(", "):String(m.noneSelected);N.textContent=r,k.textContent=h?"\u25B4":"\u25BE",a.disabled=n.disabled,y.forEach(({check:d,option:l,row:z})=>{const $=l.selected;d.textContent=$?"\u2714":"",z.setAttribute("aria-selected",String($)),z.setAttribute("aria-disabled",String(l.disabled)),z.style.cursor=l.disabled?"not-allowed":"pointer",z.style.opacity=l.disabled?"0.55":"1",z.style.backgroundColor=$?"var(--atlas-color-surface-muted, #f9fafb)":"var(--atlas-color-surface, #fff)"}),n.disabled&&h&&g({focusButton:!1})}const ue=()=>{n.dispatchEvent(new Event("input",{bubbles:!0}))},M=()=>{E()},_=e=>{const{option:t,row:o}=e;if(t.disabled)return;const r=L().length;if(!t.selected&&Number.isFinite(v)&&r>=v)if(v===1)Array.from(n.options).forEach(d=>{d.disabled||(d.selected=!1)});else{V(o);return}if(D&&t.selected&&r<=1){V(o);return}t.selected=!t.selected,M()},I=(e,t)=>{const o=Z();if(!o.length)return;const r=Math.max(0,o.findIndex(({row:l})=>l===e)),d=t==="first"?0:t==="last"?o.length-1:(r+t+o.length)%o.length;w(o[d],{focus:!0})},fe=e=>{const t=document.createElement("div");t.dataset.search=Q(e.textContent),t.setAttribute("role","option"),b(t,p.option);const o=document.createElement("span");o.textContent=e.textContent;const r=document.createElement("span");r.setAttribute("aria-hidden","true"),b(r,p.check),t.append(o,r);const d={check:r,option:e,row:t};return B(t,"click",()=>_(d)),B(t,"keydown",l=>{l.key==="Enter"||l.key===" "?(l.preventDefault(),_(d)):l.key==="ArrowDown"?(l.preventDefault(),I(t,1)):l.key==="ArrowUp"?(l.preventDefault(),I(t,-1)):l.key==="Home"?(l.preventDefault(),I(t,"first")):l.key==="End"?(l.preventDefault(),I(t,"last")):l.key==="Escape"&&(l.preventDefault(),g({focusButton:!0}))}),B(t,"mouseenter",()=>{e.disabled||(t.style.backgroundColor=e.selected?"var(--atlas-color-surface-muted, #f9fafb)":"var(--atlas-color-surface-hover, #f3f4f6)")}),B(t,"mouseleave",()=>E()),d},F=()=>{const e=y.find(({row:o})=>o===document.activeElement)?.option;O.abort(),O=new AbortController,y=Array.from(n.options,fe),x.replaceChildren(...y.map(({row:o})=>o));const t=y.find(({option:o})=>o===e)??S();w(t,{focus:h&&!!e}),T(c?.value??""),E()},ee=e=>{u.contains(e.target)||g({focusButton:!1})},pe=()=>{document.addEventListener("click",ee)},te=()=>{document.removeEventListener("click",ee)};function g({focusButton:e=!1}={}){if(!h)return;h=!1,f.hidden=!0,f.style.display="none",a.setAttribute("aria-expanded","false"),k.textContent="\u25BE",te();const t=A()!==C;C=A(),t&&ue(),e&&a.isConnected&&a.focus({preventScroll:!0})}function R({focus:e="selected"}={}){h||n.disabled||(h=!0,C=A(),f.hidden=!1,f.style.display="block",a.setAttribute("aria-expanded","true"),k.textContent="\u25B4",x.scrollTop=0,pe(),E(),c?(c.value="",T(""),c.focus({preventScroll:!0})):w(S(e),{focus:!0}))}const oe=U&&!Number.isFinite(v),re=U&&!D;if(oe||re){const e=document.createElement("div");e.className="button-container",b(e,p.buttonContainer);const t=o=>{const r=document.createElement("button");return r.type="button",r.textContent=String(o),b(r,p.actionBtn),i(r,"mouseenter",()=>{r.style.backgroundColor="var(--atlas-color-surface-hover, #f3f4f6)",r.style.borderColor="var(--atlas-color-primary, #2e7636)",r.style.color="var(--atlas-color-text-strong, #000)"}),i(r,"mouseleave",()=>{r.style.backgroundColor="var(--atlas-color-surface, #fff)",r.style.borderColor="var(--atlas-color-control-border, #d1d5db)"}),r};if(oe){const o=t(m.selectAll);i(o,"click",()=>{Array.from(n.options).forEach(r=>{r.disabled||(r.selected=!0)}),M()}),e.appendChild(o)}if(re){const o=t(m.deselectAll);i(o,"click",()=>{Array.from(n.options).forEach(r=>{r.disabled||(r.selected=!1)}),M()}),e.appendChild(o)}f.appendChild(e)}if(ae){const e=document.createElement("div");b(e,p.searchContainer),c=document.createElement("input"),c.type="search",c.placeholder=String(m.search),c.setAttribute("aria-label",String(m.search)),b(c,p.searchInput),i(c,"input",()=>T(c.value)),i(c,"keydown",t=>{t.key==="Escape"?(t.preventDefault(),g({focusButton:!0})):t.key==="ArrowDown"?(t.preventDefault(),w(S("first"),{focus:!0})):t.key==="ArrowUp"&&(t.preventDefault(),w(S("last"),{focus:!0}))}),e.appendChild(c),f.appendChild(e)}f.appendChild(x),i(a,"click",()=>{h?g():R()}),i(a,"keydown",e=>{e.key==="ArrowDown"||e.key==="ArrowUp"?(e.preventDefault(),R({focus:e.key==="ArrowDown"?"first":"last"})):e.key==="Escape"&&h&&(e.preventDefault(),g({focusButton:!0}))}),i(a,"mouseenter",()=>{a.style.borderColor="var(--atlas-color-primary, #2e7636)"}),i(a,"mouseleave",()=>{a.style.borderColor="var(--atlas-color-border, #c9c9c9)"}),i(a,"focus",()=>{a.style.borderColor="var(--atlas-color-primary, #2e7636)"}),i(u,"focusout",()=>{window.setTimeout(()=>{h&&!u.contains(document.activeElement)&&g({focusButton:!1})},0)}),i(n,"input",()=>{C=A(),E()}),i(n,"change",()=>{C=A(),E()});const ne=new MutationObserver(()=>{K(),C=A(),F()});return n.parentNode.insertBefore(u,n),u.append(a,f,n),ne.observe(n,{attributes:!0,attributeFilter:["disabled","label","selected","value"],characterData:!0,childList:!0,subtree:!0}),F(),Object.defineProperty(s,"atlasMultiSelect",{configurable:!0,value:Object.freeze({close:e=>g(e),destroy:()=>{Y||(Y=!0,te(),ne.disconnect(),O.abort(),P.abort(),u.parentNode&&(u.parentNode.insertBefore(n,u),u.remove()),G==null?n.removeAttribute("style"):n.setAttribute("style",G),s!==n&&(J==null?s.removeAttribute("style"):s.setAttribute("style",J)),delete s.atlasMultiSelect)},open:e=>R(e),refresh:F,select:n})}),s}
