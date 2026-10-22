#!/usr/bin/env python3
"""
guitare-clavier : tape du texte avec une guitare (Windows, macOS, Linux).

Le micro capte une note, on détecte sa hauteur, et on simule la frappe
de la touche associée dans l'application active.
"""
import sys
import time
import math
import threading
import numpy as np
import sounddevice as sd
from pynput.keyboard import Controller, Key

NOMS = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]

# Lettres classees par frequence en francais, puis touches speciales.
LETTRES = list("eastinrloudcmpvgbfhqjkxyzw")
SPECIAUX = [
    (" ", "espace"), ("BS", "effacer"), ("ENTER", "entree"),
    (".", "."), (",", ","), ("SHIFT", "majuscule"),
    ("'", "'"), ("?", "?"), ("!", "!"), ("-", "-"),
]
TOUCHES = [(l, l) for l in LETTRES] + SPECIAUX

BASE_MIDI = 40          # Mi2 : corde de Mi grave a vide
SR = 44100
BLOC = 2048
SEUIL = 0.012           # niveau RMS minimum
STABLE_MIN = 3          # nombre de lectures identiques avant de taper

clavier = Controller()
etat = {"maj": False, "dernier": None, "cand": None, "stable": 0,
        "rms_prec": 0.0, "texte": "", "actif": True, "octave": 0, "seuil": SEUIL}


def nom_note(m):
    return f"{NOMS[m % 12]}{m // 12 - 1}"


def detecter(x, sr, seuil):
    """Detection de hauteur (NSDF) : renvoie (rms, frequence ou None)."""
    rms = float(np.sqrt(np.mean(x * x)))
    if rms < seuil:
        return rms, None
    n = len(x) // 2
    lag_min, lag_max = int(sr / 700), int(sr / 70)
    a = x[:n]
    nsdf = np.zeros(lag_max + 2)
    for lag in range(lag_min, lag_max + 1):
        b = x[lag:lag + n]
        m = np.dot(a, a) + np.dot(b, b)
        nsdf[lag] = 2 * np.dot(a, b) / m if m > 0 else 0
    pics, positif = [], False
    for lag in range(lag_min + 1, lag_max):
        if nsdf[lag] < 0:
            positif = True
        if positif and nsdf[lag] > 0.5 and nsdf[lag] >= nsdf[lag - 1] and nsdf[lag] > nsdf[lag + 1]:
            pics.append(lag)
    if not pics:
        return rms, None
    meilleur = max(nsdf[p] for p in pics)
    lag = next(p for p in pics if nsdf[p] >= 0.9 * meilleur)
    y0, y1, y2 = nsdf[lag - 1], nsdf[lag], nsdf[lag + 1]
    d = y0 - 2 * y1 + y2
    decal = 0.5 * (y0 - y2) / d if d else 0
    return rms, sr / (lag + decal)


def taper(valeur):
    if valeur == "BS":
        clavier.tap(Key.backspace)
    elif valeur == "ENTER":
        clavier.tap(Key.enter)
    elif valeur == "SHIFT":
        etat["maj"] = not etat["maj"]
        return "majuscule " + ("ON" if etat["maj"] else "OFF")
    else:
        if etat["maj"] and len(valeur) == 1:
            valeur = valeur.upper()
            etat["maj"] = False
        clavier.type(valeur)
    return None


def traiter(x):
    rms, f = detecter(x, SR, etat["seuil"])
    prec = etat["rms_prec"]
    etat["rms_prec"] = rms
    if f is None:
        etat["stable"], etat["cand"] = 0, None
        if rms < etat["seuil"] * 0.6:
            etat["dernier"] = None
        return rms, None, None
    midi = round(69 + 12 * math.log2(f / 440))
    base = BASE_MIDI + 12 * etat["octave"]
    idx = midi - base
    if midi == etat["cand"]:
        etat["stable"] += 1
    else:
        etat["cand"], etat["stable"] = midi, 1
    repince = rms > prec * 1.8 and midi == etat["dernier"]
    tape = None
    if etat["stable"] >= STABLE_MIN and (midi != etat["dernier"] or repince):
        etat["dernier"], etat["stable"] = midi, 0
        if 0 <= idx < len(TOUCHES):
            tape = TOUCHES[idx]
            if etat["actif"]:
                taper(tape[0])
    return rms, (midi, f), tape


def afficher_mapping():
    base = BASE_MIDI + 12 * etat["octave"]
    print("\n  Mapping note -> touche")
    ligne = ""
    for i, (_, label) in enumerate(TOUCHES):
        ligne += f"{nom_note(base + i):>6} -> {label:<9}"
        if (i + 1) % 4 == 0:
            print("  " + ligne)
            ligne = ""
    if ligne:
        print("  " + ligne)
    print()


def aide():
    print("""
Commandes (tape-les puis Entree) :
  p        pause / reprise de la frappe (utile pour reprendre ton clavier)
  m        afficher le mapping
  o +|-    decaler d'une octave
  s N      seuil de sensibilite (1 a 60, defaut 12)
  q        quitter
""")


def boucle_commandes():
    aide()
    while True:
        try:
            cmd = input().strip().lower().split()
        except EOFError:
            break
        if not cmd:
            continue
        if cmd[0] == "q":
            etat["quitter"] = True
            break
        elif cmd[0] == "p":
            etat["actif"] = not etat["actif"]
            print("  frappe", "ACTIVE" if etat["actif"] else "EN PAUSE")
        elif cmd[0] == "m":
            afficher_mapping()
        elif cmd[0] == "o" and len(cmd) > 1:
            etat["octave"] += 1 if cmd[1] == "+" else -1
            print("  octave:", etat["octave"])
        elif cmd[0] == "s" and len(cmd) > 1:
            try:
                etat["seuil"] = max(1, min(60, int(cmd[1]))) / 1000
                print("  seuil:", etat["seuil"])
            except ValueError:
                print("  valeur invalide")
        else:
            aide()


def main():
    print("=" * 46)
    print(" guitare-clavier  -  pitch -> frappe clavier")
    print("=" * 46)
    print(" Place le curseur dans une autre application,")
    print(" puis joue une note nette sur ta guitare.")
    afficher_mapping()
    threading.Thread(target=boucle_commandes, daemon=True).start()

    def callback(indata, frames, temps, status):
        pass

    with sd.InputStream(channels=1, samplerate=SR, blocksize=BLOC, callback=callback) as flux:
        while not etat.get("quitter"):
            donnees, _ = flux.read(BLOC)
            x = donnees[:, 0].astype(np.float32)
            rms, note, tape = traiter(x)
            niveau = min(10, int(rms * 60))
            barre = "#" * niveau + "." * (10 - niveau)
            if note:
                txt = f"{nom_note(note[0]):<5} {note[1]:6.1f} Hz"
            else:
                txt = "-" * 14
            sortie = tape[1] if tape else ""
            etat_txt = "ON " if etat["actif"] else "PAUSE"
            sys.stdout.write(f"\r  [{barre}] {txt}  {etat_txt}  {('-> ' + sortie) if sortie else '':<14}")
            sys.stdout.flush()
    print("\nAu revoir !")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAu revoir !")
