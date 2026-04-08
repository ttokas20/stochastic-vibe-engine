"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               LIVE VIBE ENGINE — THE MASTER BRAIN                            ║
║  - Drift-Free Absolute Clock (Zero Latency/Lag)                              ║
║  - True Artist DNA (Travis/Don Markov Matrices)                              ║
║  - Dual-Layer Melodics (Groove Chords + Atmospheric Pads)                    ║
║  - Live Mixer State (Mute/Unmute components in real-time)                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import socket
import threading
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "localhost"
PORT = 8000
HTTP_PORT = 8001

# SYSTEM STATE
state = {
    "bpm": 130,
    "artist": "travis",
    "playing": False,
    "section": "verse",
    "mutes": {
        "kick": False,
        "snare": False,
        "hat": False,
        "bass": False,
        "chords": False,
        "atmos": False
    },
    "_dirty": False,
}
state_lock = threading.Lock()
client_conn = None

# =========================================================
#  ARTIST BEAT DNA 
# =========================================================
KICK_DNA = {
    "travis": {0: 1.0, 3: 0.7, 8: 0.2, 10: 0.6, 11: 0.4},
    "don":    {0: 1.0, 2: 0.3, 4: 0.2, 8: 0.8, 14: 0.5}
}

HAT_MARKOV = {
    "travis": {
        "X": {"X": 0.4, "x": 0.2, "R": 0.3, "-": 0.1},
        "x": {"X": 0.6, "x": 0.1, "R": 0.2, "-": 0.1},
        "R": {"X": 0.5, "x": 0.2, "R": 0.1, "-": 0.2},
        "-": {"X": 0.8, "x": 0.0, "R": 0.2, "-": 0.0},
    },
    "don": {
        "X": {"X": 0.3, "x": 0.5, "R": 0.05, "-": 0.15},
        "x": {"X": 0.2, "x": 0.5, "R": 0.10, "-": 0.20},
        "R": {"X": 0.4, "x": 0.4, "R": 0.00, "-": 0.20},
        "-": {"X": 0.6, "x": 0.3, "R": 0.05, "-": 0.05},
    }
}

def get_next_markov(current: str, artist: str) -> str:
    transitions = HAT_MARKOV[artist][current]
    roll = random.random()
    cum = 0.0
    for state_name, prob in transitions.items():
        cum += prob
        if roll < cum: return state_name
    return "-"

CHORD_PHRASES = {
    "travis": [[48, 55, 60, 62], [43, 50, 55, 58], [41, 48, 53, 55], [48, 55, 60, 62]],
    "don":    [[45, 52, 57, 60], [41, 48, 53, 55], [43, 50, 55, 57], [45, 52, 57, 60]]
}

# =========================================================
# HTTP CONTROL SERVER
# =========================================================
class ControlHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global state
        length = int(self.headers["Content-Length"])
        data   = self.rfile.read(length).decode().strip()

        with state_lock:
            if data.startswith("BPM:"): state["bpm"] = int(data.split(":")[1])
            elif data.startswith("ARTIST:"): state["artist"] = data.split(":")[1].lower()
            elif data.startswith("SECTION:"): state["section"] = data.split(":")[1].lower()
            elif data.startswith("TOGGLE:"):
                target = data.split(":")[1].lower()
                if target in state["mutes"]:
                    state["mutes"][target] = not state["mutes"][target]
            elif data == "PLAY": state["playing"] = True
            elif data == "STOP": state["playing"] = False

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
    def log_message(self, *_): pass

def start_http():
    server = HTTPServer(("localhost", HTTP_PORT), ControlHandler)
    server.serve_forever()

# =========================================================
# THE DRIFT-FREE MUSIC ENGINE
# =========================================================
def music_engine():
    global client_conn
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[ENGINE] Waiting for MIDI Client on port {PORT}...")
    client_conn, addr = srv.accept()
    print("[ENGINE] Client Connected. Engine Online.")

    def send(msg: str):
        try: client_conn.sendall((msg + "\n").encode())
        except OSError: pass

    step = 0
    global_step = 0
    hat_state = "X"
    next_step_time = time.time()

    while True:
        with state_lock:
            if not state["playing"]:
                time.sleep(0.05)
                next_step_time = time.time()
                continue
            bpm = state["bpm"]
            artist = state["artist"]
            section = state["section"]
            mutes = state["mutes"].copy()

        sixteenth = (60.0 / bpm) / 4.0
        
        #  rigid bounce v/s laid-back 
        swing_amount = 0.15 if artist == "travis" else 0.25
        swing_delay = sixteenth * swing_amount if step % 2 == 1 else 0.0

        bar_index = (global_step // 16) % 4
        chord = CHORD_PHRASES[artist][bar_index]
        notes_str = ",".join(map(str, chord))

        # ── 1. ATMOSPHERIC PAD ──
        if step == 0 and not mutes["atmos"]:
            # Pitch the pad up an octave for high air/atmosphere
            atmos_notes = ",".join(map(str, [n + 12 for n in chord]))
            send(f"ATMOS_ON|{atmos_notes}|65|long")

        # ── 2. RHYTHMIC CHORDS ──
        if not mutes["chords"] and section != "intro":
            if step == 0:
                send(f"SYNTH_CHORD|{notes_str}|85|short")
            elif step == 11 and section == "drop":
                send(f"SYNTH_CHORD|{notes_str}|70|short")

        # ── 3. KICK & 808 ──
        if section != "intro":
            kick_prob = KICK_DNA[artist].get(step, 0.0)
            if section == "drop": kick_prob *= 1.5 
            
            if random.random() < kick_prob:
                if not mutes["kick"]: send("KICK_ON|127")
                if not mutes["bass"]: send(f"BASS_ON|{chord[0]}|110")

        # ── 4. SNARE ──
        if section != "intro" and step in (4, 12):
            if not mutes["snare"]: send("SNARE_ON|115")

        # ── 5. MARKOV HI-HATS ──
        if section != "intro":
            hat_state = get_next_markov(hat_state, artist)
            if not mutes["hat"]:
                if hat_state == "X": send("HAT_ON|110")
                elif hat_state == "x": send("HAT_ON|60")
                elif hat_state == "R":
                    send("HAT_ON|100")
                    # Background thread fires the rapid 32nd note
                    def hat_roll(delay):
                        time.sleep(delay)
                        send("HAT_ON|80")
                    threading.Thread(target=hat_roll, args=(sixteenth / 2.0,)).start()

        # ──  DRIFT-FREE CLOCK ──
        step_duration = sixteenth + swing_delay
        next_step_time += step_duration
        
        now = time.time()
        sleep_time = next_step_time - now
        
        if sleep_time > 0: time.sleep(sleep_time)
        else: next_step_time = now # Anti-lag reset
        
        # ── NOTE OFFS ──
        send("KICK_OFF|0")
        send("SNARE_OFF|0")
        if hat_state != "R": send("HAT_OFF|0")

        step = (step + 1) % 16
        global_step += 1

if __name__ == "__main__":
    threading.Thread(target=start_http, daemon=True).start()
    music_engine()
