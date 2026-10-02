class BackToTop extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"})}connectedCallback(){this.shadowRoot.innerHTML=`
      <style>
        .back-to-top {
          position: fixed;
          bottom: calc(80px + env(safe-area-inset-bottom));
          right: calc(30px + env(safe-area-inset-right));
          padding: 12px 16px;
          font-size: 16px;
          cursor: pointer;
          opacity: 0;
          visibility: hidden;
          transition: opacity 0.3s, visibility 0.3s;
          border: none;
          border-radius: 6px;
          background-color: #333;
          color: white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
          z-index: 1000;
        }

        .back-to-top.visible {
          opacity: 1;
          visibility: visible;
        }

        .back-to-top:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }

        @media (max-width: 640px) {
          .back-to-top {
            bottom: calc(72px + env(safe-area-inset-bottom));
            right: calc(16px + env(safe-area-inset-right));
            padding: 10px 12px;
            font-size: 14px;
          }
        }
      </style>
      <button class="back-to-top" aria-label="Back to top">\u2191</button>
    `;const t=this.shadowRoot.querySelector(".back-to-top"),i=o=>o==="fr"?"Retour en haut":"Back to top";t.setAttribute("aria-label",i(document.documentElement.lang));const s=o=>t.setAttribute("aria-label",i(o.detail));window.addEventListener("atlas:lang",s);const l=window.matchMedia("(prefers-reduced-motion: reduce)");let e=!1;const n=()=>{window.scrollY>300?t.classList.add("visible"):t.classList.remove("visible"),e=!1},r=()=>{e||(e=!0,window.requestAnimationFrame(n))};window.addEventListener("scroll",r,{passive:!0}),n();const c=()=>{window.scrollTo({top:0,behavior:l.matches?"auto":"smooth"})};t.addEventListener("click",c),this._cleanup=()=>{window.removeEventListener("scroll",r),window.removeEventListener("atlas:lang",s),t.removeEventListener("click",c)}}disconnectedCallback(){this._cleanup&&this._cleanup()}updateLabel(a){const t=this.shadowRoot.querySelector(".back-to-top");t&&t.setAttribute("aria-label",a)}}customElements.define("back-to-top",BackToTop);
