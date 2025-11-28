// === Configuration ===
const API_URL = "/api/pages"; // ou l'URL relative de ton proxy Node
const duration = 13000; // ms
const RELOAD_INTERVAL = 5 * 60 * 1000; // 5 minutes

// === Références DOM ===
const carouselInner = document.querySelector("#myCarousel .carousel-inner");
const carouselIndic = document.querySelector("#myCarousel .carousel-indicators");

let carouselConfig = {
  duration: 3 ,
  loop: true,
  show_title: true,
  reload_interval:10, 
  main_title:""
};  
let pages = {}
let progressAnimFrame  = null


// === Utilitaire pour sortir le slide_duration des paramètres ===
function getActivePageDuration() {
  const activeIndex = Array.from(carouselInner.children).findIndex(
    item => item.classList.contains("active")
  );
  const page = pages[activeIndex];
  return page?.page_duration * 1000 || carouselConfig.duration * 1000;
}

// === Chargement de la configuration du carousel ===
async function loadCarouselConfig() {
  logToServer("loadCarouselConfig")
  try {
    const response = await fetch("/api/carousel-config");
    if (!response.ok) throw new Error("Impossible de charger la config carousel");
    const data = await response.json();
    carouselConfig = { ...carouselConfig, ...data };
  } catch (err) {
    logToServer("Erreur config carousel, valeurs par défaut :"+ err, "WARN");
  }
  return carouselConfig;
}

// === Chargement et normalisation des pages ===
async function loadPages() {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // recup de la config écrase la précédente
    logToServer("Update Config with : "+ JSON.stringify(data.params))
    carouselConfig = { ...carouselConfig, ...data.params };
    // Normalisation
    pages = Array.isArray(data) ? data : (data.pages || []);
    if (!pages.length) throw new Error("Aucune page à afficher");

    renderPages(pages);
      
  } catch (err) {
    console.error("Erreur de chargement des pages :", err);
    carouselInner.innerHTML = `<div class="carousel-item active">
      <div class="p-5 text-center text-danger">Erreur : ${err.message}</div>
    </div>`;
  }
  // hide the loading part
  document.getElementById("loading").style.display="none"
}
// === Création des slides ===
function renderPages(pages) {
  carouselInner.innerHTML = "";
  carouselIndic.innerHTML = "";
  pages.forEach((page, index) => {
    const div = document.createElement("div");
    div.className = "carousel-item" + (index === 0 ? " active" : "");
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

    const div_indic = document.createElement("button");
    div_indic.className = (index === 0 ? " active" : "");
    div_indic.setAttribute("data-bs-target", "#myCarousel")
    div_indic.setAttribute("data-bs-slide-to", index)
    div_indic.setAttribute("data-bs-slide-to", index)
    div_indic.setAttribute("aria-label",  page.title || page.id)

    carouselIndic.appendChild(div_indic);

    // Appel de la fonction start_[id]()
    const funcName = `start_${page.id}`;
    if (typeof window[funcName] === "function") {
      try { window[funcName](); }
      catch(e) { logToServer(`Erreur dans ${funcName}:`+ e, "ERROR"); }
    }
  });
}

// === Initialisation du carousel Bootstrap ===
function initBootstrapCarousel() {
  if (progressAnimFrame) {
    cancelAnimationFrame(progressAnimFrame);
    progressAnimFrame = null;
  }

  setTimeout(() => {
    const carouselEl = document.getElementById("myCarousel");
    const progressCircle = document.querySelector('.global-progress-circle-fg');
    if (!progressCircle) return;

    if (carouselEl) {
      const carousel = new bootstrap.Carousel(carouselEl, {
        interval: false,
        wrap: carouselConfig.loop,
        pause: false
      });

      // Fonction pour réinitialiser le spinner
      function resetProgressCircle() {
        progressCircle.style.strokeDashoffset = '283';
        progressCircle.style.transition = 'none';
        void progressCircle.offsetWidth;
        progressCircle.style.transition = 'stroke-dashoffset 0.1s linear';
      }

      // Fonction pour démarrer l'animation du spinner
      function startProgressCircle() {
        cancelAnimationFrame(progressAnimFrame);
        resetProgressCircle();
        const duration = getActivePageDuration();
        const start = Date.now();
        const initialOffset = 283;

        function updateProgress() {
          
          const elapsed = Date.now() - start;
          const progress = Math.min(elapsed / duration, 1);
          const offset = initialOffset * (1 - progress);
          progressCircle.style.strokeDashoffset = offset;

          if (progress < 1) {
            progressAnimFrame = requestAnimationFrame(updateProgress);
          } else {
            carousel.next();
          }
        }

        progressAnimFrame = requestAnimationFrame(updateProgress);
      }

      // Écouter les changements de slide pour réinitialiser le spinner
      carouselEl.addEventListener('slid.bs.carousel', () => {
        // Attendre la fin de la transition CSS (600 ms) avant de relancer le spinner
        setTimeout(startProgressCircle, 50);
        if (progressAnimFrame) {
          cancelAnimationFrame(progressAnimFrame);
          progressAnimFrame = null;
        }
      });

      // Démarrer le spinner pour la première slide
      startProgressCircle();
    }
  }, 1500);
}

// affichage de l'heure
function updateCurrentTime() {
  const timeEl = document.getElementById("current-time");
  if (!timeEl) return;

  const now = new Date();

  // Heure
  const hours = String(now.getHours()).padStart(2,'0');
  const minutes = String(now.getMinutes()).padStart(2,'0');
  const seconds = String(now.getSeconds()).padStart(2,'0');

  // Jour de la semaine et mois en français
  const days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
  const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"];

  const dayName = days[now.getDay()];
  const dayNum = now.getDate();
  const monthName = months[now.getMonth()];
  const year = now.getFullYear();

  // Affichage
  timeEl.innerHTML = `<span class="main-title">${carouselConfig.main_title} </span><span class="time-display">${hours}:${minutes}:${seconds} - ${dayName} ${dayNum} ${monthName} ${year}</span>`;
  
}


// pour le reload des pages
async function reloadPages() {
  logToServer('.......reloading pages ......')
  try {

    // Nettoyer le timer avant de relancer
    if (progressAnimFrame) {
      cancelAnimationFrame(progressAnimFrame);
      progressAnimFrame = null;
    }
    loadPages(); 
    initBootstrapCarousel();

  } catch (err) {
    logToServer("Erreur rechargement des pages :"+ err, "ERROR");
  }
}

function setupReload(){
  setInterval(reloadPages, carouselConfig.reload_interval * 60 * 1000 || RELOAD_INTERVAL );
  setInterval(updateCurrentTime, 1000);
}

// fonction de log
async function logToServer(message, level = "info") {
  try {
    const response = await fetch("/api/log", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, level }),
    });
    if (!response.ok) {
      console.error("Erreur lors de l'envoi du log au serveur");
    }
  } catch (err) {
    console.error("Erreur réseau :", err);
  }
}

// === Démarrage ===
loadCarouselConfig()
  .then(() => loadPages())
  .then(() => initBootstrapCarousel())
  .then(()=> setupReload())
  .catch(err => logToServer(err, "ERROR"));