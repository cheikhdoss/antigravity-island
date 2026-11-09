# Master Plan & Architecture — Antigravity Island

> **Vision** : Antigravity Island est l'extension physique et visuelle d'Antigravity sur le bureau Windows — un véritable « troisième bras » et une extension permanente du mode Voice Call. Toujours visible au sommet de l'écran (0 px gap), il permet à Antigravity de voir l'écran, d'écouter, de parler, d'afficher ses réflexions et de désigner avec précision n'importe quel élément sur l'écran de l'utilisateur grâce à un pointeur laser virtuel inspiré de HeyClicky.

---

## 📊 Tableau d'Avancement Global

| Phase | Description | Statut | Livrables Clés |
|---|---|---|---|
| **Phase 1** | Interface Visuelle & Double Style (Notch iPhone X + Dynamic Island) | ✅ **100% Terminé** | PyQt6 60 FPS, 0px flush header, Obsidian Glass, 5 états morphiques, Centre de contrôle GUI |
| **Phase 2** | Persistance Système & Raccourci Global Push-to-Talk | ✅ **100% Terminé** | Stockage persistant `%APPDATA%`, Hotkey global `Win + Alt` (Hybride tap/hold), CSS haute lisibilité |
| **Phase 3** | Primitives HeyClicky (Vision MSS & Pointeur Laser) | ✅ **100% Terminé** | Capture ultra-rapide MSS, Calque de pointage laser radar transparent aux clics, FastMCP étendu |
| **Phase 4** | Moteur Audio & Transcription Vocale (STT Réactif) | ⏳ **En cours / Prochaine étape** | Capture micro locale, jauge de puissance audio en direct sur la waveform, transcription STT |
| **Phase 5** | Boucle Vocale & Vision Autonome (Antigravity Brain) | 📋 **À réaliser** | Déclenchement automatique : Win+Alt relâché -> Snapshot + Transcription -> Prompt Antigravity |
| **Phase 6** | Synthèse Vocale (TTS) & Lip-Sync de l'Égaliseur | 📋 **À réaliser** | Sortie voix naturelle (Edge-TTS / ElevenLabs) synchronisée avec l'égaliseur de l'encoche |
| **Phase 7** | Automatisation Bureau & Sécurité (Computer Use) | 📋 **À réaliser** | Clics guidés, saisie, raccourcis avec confirmation utilisateur préalable |
| **Phase 8** | Finitions Système & Packaging Production | 📋 **À réaliser** | Démarrage avec Windows, support multi-écrans, installateur standalone |

---

## 🛠️ Détail des Phases & Tâches Restantes

### Phase 4 : Moteur Audio & Transcription Vocale (STT Réactif)
*Objectif : Donner des oreilles à l'encoche et animer la waveform sonore en direct quand l'utilisateur parle.*

- [ ] **4.1 Capture du Flux Microphone**
  - Utilisation de `sounddevice` ou `PyAudio` pour écouter le périphérique d'entrée par défaut sous Windows.
  - Activation de l'écoute uniquement pendant l'état `listening` (Push-to-Talk `Win + Alt` actif).
- [ ] **4.2 Jauge RMS & Animation Réactive de la Waveform**
  - Calcul de l'énergie acoustique (RMS / dB) en temps réel à 60 FPS.
  - Transmission du niveau sonore vers `WaveformVisualizer` pour que les barres de l'encoche dansent au son exact de la voix de l'utilisateur.
- [ ] **4.3 Moteur de Transcription Vocale (Speech-to-Text)**
  - Option A (Ultra-rapide Cloud) : Intégration de l'API Groq Whisper (latence < 250ms) ou Deepgram / AssemblyAI.
  - Option B (Local / Hors-ligne) : Intégration de `faster-whisper` (modèle `base` ou `small` sur CPU/GPU).
  - Prévisualisation du texte en cours de dictée directement dans l'encoche sous le libellé "À votre écoute...".

---

### Phase 5 : Boucle Autonome Antigravity ("Le Troisième Bras")
*Objectif : Relier la voix, la vision et l'intelligence de l'agent sans friction.*

- [ ] **5.1 Orchestration Automatique Post-Écoute**
  - Dès relâchement du raccourci `Win + Alt` :
    1. L'encoche bascule instantanément en état `thinking` ("Analyse en cours...").
    2. Une capture d'écran est automatiquement déclenchée via `island.vision.capture_screen()`.
    3. Le texte transcrit et la capture d'écran sont transmis au contexte d'Antigravity.
- [ ] **5.2 Réponse Multi-Canaux d'Antigravity**
  - Antigravity génère sa réponse et pilote simultanément :
    - `island_speak(text)` : Affiche le résumé de la réponse au sommet de l'écran.
    - `island_point_at(x, y, label)` : Désigne le bouton ou l'erreur spécifique analysée sur l'écran.
    - `island_action(title, detail, progress)` : Déroule les étapes d'une tâche complexe.
- [ ] **5.3 Gestion de l'Interruption (Barge-in)**
  - Si l'utilisateur réappuie sur `Win + Alt` pendant qu'Antigravity parle, l'agent coupe immédiatement sa parole et repasse en écoute active.

---

### Phase 6 : Synthèse Vocale (TTS) & Lip-Sync
*Objectif : Permettre à Antigravity de répondre vocalement avec un son limpide synchronisé à l'encoche.*

- [ ] **6.1 Moteur de Synthèse Vocale (TTS)**
  - Intégration d'un moteur TTS expressif à très faible latence :
    - Option 1 : `edge-tts` (voix françaises Henri / Denise de Microsoft Azure, 100% gratuites, naturelles et sans clé API requise).
    - Option 2 : `ElevenLabs` pour un réalisme vocal maximal.
- [ ] **6.2 Synchronisation Audio-Waveform (Lip-Sync Visuel)**
  - Lecture du flux audio de réponse via un canal analysé (FFT / RMS).
  - Animation de l'égaliseur cyan/émeraude sur l'encoche pendant que la voix retentit dans les haut-parleurs.
  - Retour automatique en mode `idle` (encoche compacte au repos) 1,5 seconde après la fin de la parole.

---

### Phase 7 : Automatisation & Interactions Bureau (Computer Use)
*Objectif : Donner la capacité d'agir concrètement sur l'ordinateur comme HeyClicky.*

- [ ] **7.1 Moteur d'Actions Contrôlées**
  - Déplacement fluide du curseur le long de courbes de Bézier vers une cible (`pyautogui` ou `win32api`).
  - Simulation de clics de souris gauche/droit et défilement.
  - Saisie de texte dans les champs actifs.
- [ ] **7.2 Garde-Fous & Sécurité (Safety Gate)**
  - Demande d'approbation visuelle sur l'encoche avant toute action sensible ou destructive.
  - Raccourci d'arrêt d'urgence instantané (`Échap` ou secousse de souris).

---

### Phase 8 : Finitions Système & Packaging Production
*Objectif : Rendre l'application prête pour un usage quotidien fluide et invisible.*

- [ ] **8.1 Lancement Automatique avec Windows**
  - Option dans le Centre de contrôle pour activer/désactiver le démarrage automatique au boot via le registre Windows (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- [ ] **8.2 Support Multi-Moniteurs Avancé**
  - Sélecteur d'écran dans le Centre de contrôle pour choisir d'ancrer l'encoche sur l'Écran 1, l'Écran 2, etc.
- [ ] **8.3 Packaging Final & Auto-Installation**
  - Script de packaging unique produisant un installateur Windows propre ou un binaire portable complet.
  - Nettoyage des logs et optimisation de la mémoire vive (< 65 Mo de RAM en veille).

---

## 📌 Architecture Technique Actuelle

```
antigravity-island/
├── assets/
│   ├── app_icon.ico                 # Icône officielle de l'application
│   └── app_icon.png
├── island/
│   ├── components/
│   │   ├── glowing_orb.py           # Orbe cosmique d'état Thinking
│   │   └── waveform.py              # Égaliseur audio 60 FPS
│   ├── config.py                    # Constantes de design, couleurs et dimensions
│   ├── hotkey.py                    # Moteur Push-to-Talk (Win + Alt global pynput)
│   ├── pointer.py                   # Pointeur laser virtuel et étiquette (Clicky)
│   ├── vision.py                    # Capture d'écran instantanée MSS
│   ├── server.py                    # Serveur WebSocket ws://127.0.0.1:8765
│   ├── settings_window.py           # Centre de contrôle & persistance %APPDATA%
│   └── window.py                    # Fenêtre de l'encoche (iPhone X Notch & Island)
├── main.py                          # Point d'entrée principal & System Tray Windows
├── mcp_server.py                    # Serveur FastMCP (Outils Antigravity)
└── PLAN.md                          # Ce document maître
```

---

*Dernière mise à jour : 09 Novembre 2026 — Maintenu par Antigravity & Cheikh Doss.*
