# Master Plan — Antigravity Island : L'Extension du Mode Voice Call

> **Principe Fondateur** : Antigravity Island ne réinvente pas de moteur vocal externe (pas de TTS tiers comme Edge-TTS ou ElevenLabs, pas de serveur Whisper séparé).  
> **Antigravity possède DÉJÀ sa propre voix native (mode Voice Call), son écoute et son intelligence multimodale.**  
> Antigravity Island constitue ses **organes sensoriels et son « troisième bras » sur le bureau Windows** :
> 1. **Le Visage** : L'encoche (Notch iPhone X / Dynamic Island) qui exprime visuellement ses états (écoute, réflexion, parole, actions).
> 2. **Les Yeux** : La capture d'écran instantanée MSS (`island_capture_screen`) qui lui permet de voir ce que l'utilisateur regarde.
> 3. **Le Bras** : Le pointeur laser virtuel (`island_point_at`) qui lui permet de désigner un élément précis à l'écran pendant qu'il parle.
> 4. **L'Oreille (Trigger)** : Le raccourci global `Win + Alt` au niveau OS pour l'interpeller d'un geste.
> 5. **Le Contrôle MCP** : Antigravity pilote l'ensemble de façon autonome via ses outils MCP natifs.

---

## 📊 Matrice d'Intégration Antigravity

```
┌────────────────────────────────────────────────────────────────────────┐
│                      CERVEAU : ANTIGRAVITY                             │
│       • Mode Voice Call Natif (Voix & Écoute intégrées)                │
│       • Intelligence Multimodale (Raisonnement & Vision)               │
└──────────────────┬──────────────────────────────────▲──────────────────┘
                   │ Pilote via MCP                   │ Déclenche & informe
                   │ (speak, point_at, action)        │ (Win + Alt, capture)
┌──────────────────▼──────────────────────────────────┴──────────────────┐
│              ORGANES : ANTIGRAVITY ISLAND (Windows)                    │
│                                                                        │
│  [ LE VISAGE ]     Encoche iPhone X & Dynamic Island (0px gap header) │
│  [ LES YEUX ]      Capture d'écran 60 FPS ultra-rapide MSS             │
│  [ LE BRAS ]       Pointeur laser & halo radar sur l'écran (HeyClicky)│
│  [ LE TRIGGER ]    Raccourci global matériel [ Win + Alt ]             │
│  [ LE CONTRÔLE ]   Serveur WebSocket local ws://127.0.0.1:8765         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🏆 Avancement & Feuille de Route Réelle

### Ce qui est DÉJÀ Réalisé & Opérationnel ✅
- [x] **Visuel Haute Fidélité (0 px gap header)** :
  - Double style : Encoche iPhone X (cornes concaves, grille haut-parleur) & Dynamic Island.
  - 5 états morphiques fluides (Idle avec point à gauche, Écoute, Réflexion, Parole, Action).
  - Finition Obsidian Glass (#0a0a0e), bordures hairlines, animations spring 60 FPS.
- [x] **Persistance des Paramètres Windows** :
  - Sauvegarde permanente dans `%APPDATA%\AntigravityIsland\settings.json`.
  - Rechargement instantané à chaque démarrage sans perte de configuration.
  - Centre de contrôle avec sliders de taille, alignement, styles et contraste élevé.
- [x] **Raccourci Global Push-to-Talk** :
  - Détection OS globale des touches `Win + Alt` (mode hybride tap court = toggle / maintien = push-to-talk).
- [x] **Organes HeyClicky & Computer Use intégrés** :
  - Vision instantanée MSS : `island_capture_screen()`.
  - Pointeur laser virtuel click-through : `island_point_at(x, y, label)`.
  - Détection OCR native Windows 10/11 sans dépendance : `island_find_elements(query)`.
  - Contrôle souris fluide Bézier (courbe cubique + easing) : `island_click(x, y)`, `island_move_cursor(x, y)`.
  - Clic automatique par recherche d'élément : `island_click_element(query)`.
  - Saisie clavier Unicode (accents complets) : `island_type(text)`.
  - Combinaisons de touches : `island_press_key(key)`.
  - Défilement molette : `island_scroll(amount)`.
- [x] **Serveur MCP Complet & Enregistré** :
  - Outils `island_find_elements`, `island_click`, `island_click_element`, `island_type`, `island_press_key`, `island_scroll`, `island_move_cursor`, `island_speak`, `island_action`, `island_point_at`, `island_capture_screen`, `island_get_screen_info`, `island_set_style`, `island_idle`, `island_set_state`, `island_audio_pulse`.
- [x] **Démarrage Automatique & Multi-Écrans** :
  - Clé de registre Windows Run configurée et testée via le Centre de Contrôle.
  - Sélecteur de moniteur avec détection dynamique de résolution.

---

### Ce qu'il Reste à Réaliser (Les 3 Étapes Clés) ⏳

### Étape 1 : Connexion Bidirectionnelle Voice Call $\leftrightarrow$ Encoche
*Objectif : Synchroniser le mode Voice Call natif d'Antigravity avec les battements de l'encoche.*

- [ ] **1.1 Liaison de l'Animation de Parole (Voice $\rightarrow$ Island)**
  - Lorsque la voix d'Antigravity parle dans le Voice Call :
    - L'encoche passe automatiquement en mode `speaking`.
    - La waveform / l'égaliseur pulse au rythme de sa voix (`island_audio_pulse` ou modulation automatique).
    - Le texte clé résumé de ce qu'Antigravity dit apparaît sur l'encoche (`island_speak`).
- [ ] **1.2 Liaison de l'Écoute (Win + Alt $\rightarrow$ Voice Call)**
  - Lorsque l'utilisateur enfonce `Win + Alt` :
    - L'encoche s'ouvre en mode `listening`.
    - L'onde sonore réagit à la présence de la voix de l'utilisateur.
    - Dès que l'utilisateur relâche `Win + Alt`, l'encoche passe en `thinking` pendant qu'Antigravity réfléchit.

---

### Étape 2 : Le Réflexe Visuel Autonome ("Le Troisième Bras")
*Objectif : Permettre à Antigravity de montrer ce dont il parle pendant la conversation vocale.*

- [ ] **2.1 Capture d'Écran Contextuelle Instantanée**
  - Dès que l'utilisateur pose une question en mode vocal ("Regarde ce bouton", "Pourquoi cette erreur s'affiche ?") :
    - Antigravity appelle automatiquement `island_capture_screen()`.
    - Antigravity analyse l'image capturée pour comprendre immédiatement le contexte visuel de l'utilisateur.
- [ ] **2.2 Pointage Laser Spontané**
  - Pendant qu'Antigravity explique la solution à la voix :
    - Il appelle spontanément `island_point_at(x, y, "Clique ici")` sur les coordonnées du bouton ou de la zone concernée.
    - Le halo radar cyan/émeraude pulse à l'écran sous les yeux de l'utilisateur.

---

### Étape 3 : Actions & Intégration Système Finale
*Objectif : Confort quotidien et démarrage transparent.*

- [ ] **3.1 Démarrage Automatique avec Windows**
  - Option 1-clic dans le Centre de contrôle pour que l'encoche soit toujours là au démarrage du PC sans avoir à cliquer sur un script.
- [ ] **3.2 Support Multi-Écrans**
  - Permettre de choisir sur quel moniteur l'encoche et les pointeurs laser doivent s'ancrer si l'utilisateur a plusieurs écrans.
- [ ] **3.3 Packaging Final Portable & Robuste**
  - Exécutable unique finalisé sur le Bureau avec gestion d'erreurs et empreinte mémoire minimale (< 50 Mo).

---

*Mis à jour le 09 Novembre 2026 — Architecture 100% alignée avec Antigravity Voice Call.*
