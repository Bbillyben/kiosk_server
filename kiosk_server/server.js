import express from "express";
import fetch from "node-fetch";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const app = express();
const PORT = 8080; // tu peux le changer si nécessaire

// Résolution des chemins
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Charger la config côté serveur
const config = JSON.parse(fs.readFileSync(path.join(__dirname, "config.json"), "utf-8"));
// Servir les fichiers HTML depuis ./web
app.use(express.static(path.join(__dirname, "web")));
app.use((req, res, next) => {
  console.log(`[REQ] ${req.method} ${req.url}`);
  next();
});

// Proxy vers ton API Django
app.get("/api/pages", async (req, res) => {
  try {
    const response = await fetch(config.api_url, {
      headers: {
        "Authorization": `Token ${config.token}`,
      },
    });

    if (!response.ok) {
      return res.status(response.status).send(`Erreur API: ${response.statusText}`);
    }

    const data = await response.text();
    res.send(data);
  } catch (err) {
    console.error("Erreur proxy:", err);
    res.status(500).send("Erreur de connexion au serveur distant");
  }
});

// Endpoint public pour le carousel (front-end)
app.get("/api/carousel-config", (req, res) => {
  res.json(config.carousel || {}); // expose uniquement l’objet carousel
});

// Lancer le serveur
app.listen(PORT, "0.0.0.0", () => {
  console.log(`✅ Serveur Node.js accessible sur http://<IP_RPI>:${PORT}`);
});