// === Configuration ===
const API_URL = "/api/pages"; // ou l'URL relative de ton proxy Node
const duration = 13000; // ms
const RELOAD_INTERVAL = 5 * 60 * 1000; // 5 minutes

// === Références DOM ===
const carouselInner = document.querySelector("#myCarousel .carousel-inner");
const carouselIndic = document.querySelector("#myCarousel .carousel-indicators");

let carouselConfig = {
  duration: 3000,
  loop: true,
  show_title: true,
  reload_interval:10
};  
let pages = {}

// === Chargement de la configuration du carousel ===
async function loadCarouselConfig() {
  try {
    const response = await fetch("/api/carousel-config");
    if (!response.ok) throw new Error("Impossible de charger la config carousel");
    const data = await response.json();
    carouselConfig = { ...carouselConfig, ...data };
    console.log("[Carousel config]", carouselConfig);
  } catch (err) {
    console.warn("Erreur config carousel, valeurs par défaut :", err);
  }
}

// === Chargement et normalisation des pages ===
async function loadPages() {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // recup de la config écrase la précédente
    console.log("data params :",data);
    carouselConfig = { ...carouselConfig, ...data.params };
    console.log("[Carousel config] NEW", carouselConfig);
    // Normalisation
    pages = Array.isArray(data) ? data : (data.pages || []);
    if (!pages.length) throw new Error("Aucune page à afficher");

    renderPages(pages);
    // hide the loading part
      
  } catch (err) {
    console.error("Erreur de chargement des pages :", err);
    carouselInner.innerHTML = `<div class="carousel-item active">
      <div class="p-5 text-center text-danger">Erreur : ${err.message}</div>
    </div>`;
  }
  document.getElementById("loading").style.display="none"
}
// === Création des slides ===
function renderPages(pages) {
  // while (carouselInner.firstChild) carouselInner.removeChild(carouselInner.firstChild);
  carouselInner.innerHTML = "";
  carouselIndic.innerHTML = "";
  pages.forEach((page, index) => {
    const div = document.createElement("div");
    div.className = "carousel-item" + (index === 0 ? " active" : "");
    //div.innerHTML = page.html || `<div class="p-3"><h3>${page.title || "Sans titre"}</h3></div>`;
    inner = `<div class="page-content">${page.html || `<h3>${page.title || "Sans titre"}</h3>`}`;

    if(page.title && carouselConfig.show_title){
        inner += `<div class="carousel-caption d-none d-md-block"><h5>${page.title}</h5></div>`;
    }
    inner += '</div>';
    
      
    div.innerHTML = inner;


    // Injecter et exécuter scripts inline/externe
    const scripts = div.querySelectorAll("script");
    scripts.forEach(oldScript => {
      const newScript = document.createElement("script");
      if (oldScript.src) {
        newScript.src = oldScript.src;
      } else {
        newScript.textContent = oldScript.textContent;
      }
      document.body.appendChild(newScript);
      oldScript.remove();
    });

    carouselInner.appendChild(div);

    //Indicators : 
    //<button type="button" data-bs-target="#myCarousel" data-bs-slide-to="0" class="active" aria-current="true" aria-label="Slide 1">test 2</button>
    
    const div_indic = document.createElement("button");
    div_indic.className = (index === 0 ? " active" : "");
    div_indic.setAttribute("data-bs-target", "#myCarousel")
    div_indic.setAttribute("data-bs-slide-to", index)
    div_indic.setAttribute("data-bs-slide-to", index)
    div_indic.setAttribute("aria-label",  page.title || page.id)
    // div_indic.innerHTML = page.title || page.id ;

    carouselIndic.appendChild(div_indic);

    // Appel de la fonction start_[id]()
    const funcName = `start_${page.id}`;
    if (typeof window[funcName] === "function") {
      try { window[funcName](); }
      catch(e) { console.error(`Erreur dans ${funcName}:`, e); }
    }
  });
}

// === Initialisation du carousel Bootstrap ===
function initBootstrapCarousel() {

  setTimeout(() => {
    const carouselEl = document.getElementById("myCarousel");
    if (carouselEl) {
      const carousel = new bootstrap.Carousel(carouselEl, {
        interval: carouselConfig.duration,
        wrap: carouselConfig.loop,
        ride: 'carousel',
        pause: false
      });
      console.log("✅ Carousel Bootstrap démarré");
    }
  }, 500); // 100ms suffit pour que Chromium ait rendu le DOM

}


async function reloadPages() {
  console.log('.......reloading pages ......')
  try {
    const response = await fetch("/api/pages");   
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // Normalisation
    let newPages = [];
    if (Array.isArray(data)) {
      newPages = data;
    } else if (data && Array.isArray(data.pages)) {
      newPages = data.pages;
    } else {
      throw new Error("Format de réponse invalide");
    }

    pages = newPages;
    renderPages(pages);        // reconstruire le carousel
    initBootstrapCarousel(); // réinitialiser le carousel Bootstrap

  } catch (err) {
    console.error("Erreur rechargement des pages :", err);
  }
}

function setupReload(){
  console.log("setup reload interval :"+(carouselConfig.reload_interval ))
  setInterval(reloadPages, carouselConfig.reload_interval * 60 * 1000 || RELOAD_INTERVAL );
}

// === Démarrage ===
// loadPages().then(loadCarouselConfig().then(initBootstrapCarousel));
loadCarouselConfig()
  .then(() => loadPages())
  .then(() => initBootstrapCarousel())
  .then(()=> setupReload())
  .catch(err => console.error(err));

