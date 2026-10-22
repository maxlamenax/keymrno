# guitare-clavier (Windows / macOS / Linux)

Tape du texte avec ta guitare : le micro capte une note, le programme
la convertit en lettre et simule la frappe dans l'application active.

## Installation

    pip install sounddevice numpy pynput

## Lancement

    python guitare_clavier.py

Clique ensuite dans l'application où tu veux écrire (bloc-notes, navigateur...)
et joue une note nette. Commande `p` pour mettre en pause.

## Droits système

- macOS : Réglages > Confidentialité > Accessibilité (pour le terminal),
  et Microphone.
- Linux : fonctionne sous X11. Sous Wayland, pynput est limité.
- Windows : rien à configurer.

## Créer un exécutable (optionnel)

    pip install pyinstaller
    pyinstaller --onefile guitare_clavier.py

L'exécutable est dans le dossier dist/.
