import{readNotebookConfig as m}from"./notebook.js";const d="http://www.w3.org/2000/svg";function h(){const t=document.createElementNS(d,"svg");t.classList.add("atlas-hero__mark"),t.setAttribute("viewBox","0 0 32 27");const e=document.createElementNS(d,"path");return e.setAttribute("fill","white"),e.setAttribute("stroke","white"),e.setAttribute("stroke-width",".5"),e.setAttribute("d",`M 31.60,25.63
           C 31.60,25.84 31.52,26.03 31.38,26.18
             31.23,26.32 31.04,26.40 30.84,26.40
             30.84,26.40 1.16,26.40 1.16,26.40
             0.96,26.40 0.76,26.32 0.62,26.18
             0.48,26.03 0.40,25.84 0.40,25.63
             0.40,25.43 0.48,25.24 0.62,25.09
             0.76,24.95 0.96,24.87 1.16,24.87
             1.16,24.87 2.59,24.87 2.59,24.87
             2.59,24.87 2.59,14.63 2.59,14.63
             2.59,14.42 2.67,14.23 2.82,14.09
             2.96,13.94 3.15,13.86 3.36,13.86
             3.36,13.86 8.85,13.86 8.85,13.86
             9.06,13.86 9.25,13.94 9.39,14.09
             9.54,14.23 9.62,14.42 9.62,14.63
             9.62,14.63 9.62,24.87 9.62,24.87
             9.62,24.87 12.49,24.87 12.49,24.87
             12.49,24.87 12.49,6.92 12.49,6.92
             12.49,6.72 12.57,6.52 12.71,6.38
             12.85,6.24 13.05,6.16 13.25,6.16
             13.25,6.16 18.75,6.16 18.75,6.16
             18.95,6.16 19.14,6.24 19.29,6.38
             19.43,6.52 19.51,6.72 19.51,6.92
             19.51,6.92 19.51,24.87 19.51,24.87
             19.51,24.87 22.38,24.87 22.38,24.87
             22.38,24.87 22.38,0.77 22.38,0.77
             22.38,0.56 22.46,0.37 22.60,0.22
             22.75,0.08 22.94,0.00 23.14,0.00
             23.14,0.00 28.64,0.00 28.64,0.00
             28.84,0.00 29.04,0.08 29.18,0.22
             29.32,0.37 29.40,0.56 29.40,0.77
             29.40,0.77 29.40,24.87 29.40,24.87
             29.40,24.87 30.84,24.87 30.84,24.87
             31.04,24.87 31.23,24.95 31.38,25.09
             31.52,25.24 31.60,25.43 31.60,25.63 Z`),t.appendChild(e),t}export function atlasHero({title:t,image:e,group:a="",alt:l=""}={}){if(!t)throw new TypeError("atlasHero requires a title");if(!e)throw new TypeError("atlasHero requires an image");const o=document.createElement("section");o.id="hero-image",o.className="atlas-hero",o.setAttribute("aria-labelledby","notebook-title");const r=document.createElement("img");r.className="atlas-hero__image",r.src=e,r.alt=l;const n=document.createElement("div");n.className="atlas-hero__content";const i=document.createElement("div");if(i.className="atlas-hero__icon",i.setAttribute("aria-hidden","true"),i.appendChild(h()),n.appendChild(i),a){const c=document.createElement("span");c.className="atlas-hero__group",c.textContent=String(a),n.appendChild(c)}const s=document.createElement("h1");return s.id="notebook-title",s.className="atlas-hero__title",s.textContent=String(t),n.appendChild(s),o.append(r,n),o}export function heroImage(t,e,a=""){return atlasHero({title:t,image:e,group:a})}class g extends HTMLElement{connectedCallback(){const e=m(),a=atlasHero({title:e.title?.en??e.id,image:e.image,alt:e.imageAlt?.en??""});this.replaceChildren(a);const l=a.querySelector("#notebook-title"),o=a.querySelector(".atlas-hero__image"),r=n=>{l.textContent=e.title?.[n]??e.title?.en??e.id,o.alt=e.imageAlt?.[n]??e.imageAlt?.en??""};this._onLanguageChange=n=>r(n.detail),window.addEventListener("atlas:lang",this._onLanguageChange),r(window.atlasLang??document.documentElement.lang)}disconnectedCallback(){window.removeEventListener("atlas:lang",this._onLanguageChange)}}customElements.define("atlas-notebook-hero",g);
