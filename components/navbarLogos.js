/**
 * Navbar Partner Logo Injection
 * Dynamically mounts the CGIAR Climate Action partner logo alongside
 * the Africa Agriculture Adaptation Atlas logo in the top navbar.
 */
(function () {
  function injectTopNavbarLogos() {
    const brandContainer = document.querySelector(".navbar-brand-container");
    if (brandContainer && !document.getElementById("navbarCaspLogo")) {
      brandContainer.style.display = "flex";
      brandContainer.style.alignItems = "center";

      const divider = document.createElement("span");
      divider.id = "navbarLogoDivider";
      divider.setAttribute("aria-hidden", "true");
      divider.style.cssText =
        "height: 24px; width: 1px; background: #cbd5e1; margin: 0 0.85rem; display: inline-block; flex-shrink: 0;";

      const caspLink = document.createElement("a");
      caspLink.id = "navbarCaspLogo";
      caspLink.href = "https://www.cgiar.org/initiative/climate-action/";
      caspLink.target = "_blank";
      caspLink.rel = "noopener";
      caspLink.title = "CGIAR Climate Action";
      caspLink.className = "navbar-brand navbar-brand-partner";
      caspLink.style.cssText =
        "display: inline-flex; align-items: center; padding: 0; margin: 0;";

      const existingImg = brandContainer.querySelector(".navbar-logo, img");
      const logoSrc = (existingImg && existingImg.src)
        ? existingImg.src.replace(/atlas-logo\.svg.*/, "CASP_logo.svg")
        : "/images/CASP_logo.svg";

      const caspImg = document.createElement("img");
      caspImg.src = logoSrc;
      caspImg.alt = "CGIAR Climate Action Logo";
      caspImg.style.cssText =
        "height: 32px; width: auto; max-width: 130px; object-fit: contain;";

      caspLink.appendChild(caspImg);
      brandContainer.appendChild(divider);
      brandContainer.appendChild(caspLink);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectTopNavbarLogos);
  } else {
    injectTopNavbarLogos();
  }
})();
