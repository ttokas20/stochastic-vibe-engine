"""
╔══════════════════════════════════════════════════════════════════╗
║           LIVE VIBE ENGINE — MIDI CLIENT v2                     ║
║   Connects to brains.py on localhost:8000                       ║
║   Translates IPC command strings → MIDI output                  ║
╚══════════════════════════════════════════════════════════════════╝

Dependencies:
    pip install python-rtmidi

MIDI Channel Mapping:
    Ch 10 (idx 9)  — Drums (kick, snare, hi-hat closed & open)
    Ch 1  (idx 0)  — 808 Bass
    Ch 2  (idx 1)  — Synth 

Run BEFORE brains.py:
    python receiver.py
"""

import socket
import time
import threading

try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    print("[WARN] python-rtmidi not found — running in CONSOLE MODE.")
    print("       Install with:  pip install python-rtmidi\n")

# ─────────────────────────────────────────────────────────────────
# MIDI CONSTANTS
# ─────────────────────────────────────────────────────────────────
MIDI_NOTE_ON  = 0x90
MIDI_NOTE_OFF = 0x80

DRUM_CHANNEL  = 9   # GM channel 10 (zero-indexed)
BASS_CHANNEL  = 0   # GM channel 1
SYNTH_CHANNEL = 1   # GM channel 2

KICK_NOTE       = 36   # C1
SNARE_NOTE      = 38   # D1
HAT_CLOSED_NOTE = 42   # F#1
HAT_OPEN_NOTE   = 46   # A#1

SYNTH_LONG_DUR  = 1.5
SYNTH_SHORT_DUR = 0.12
BASS_DUR        = 0.28

# ─────────────────────────────────────────────────────────────────
# MIDI OUTPUT WRAPPER
# ─────────────────────────────────────────────────────────────────
class MidiOut:
    def __init__(self):
        self.midi = None
        if RTMIDI_AVAILABLE:
            self.midi = rtmidi.MidiOut()
            ports = self.midi.get_ports()
            if ports:
                preferred = [i for i, p in enumerate(ports)
                             if any(k in p.lower() for k in ("loop", "bus", "iac", "virtual", "synth"))]
                idx = preferred[0] if preferred else 0
                self.midi.open_port(idx)
                print(f"[MIDI] Opened port: {ports[idx]}")
            else:
                self.midi.open_virtual_port("LiveVibeEngine")
                print("[MIDI] Opened virtual port 'LiveVibeEngine'.")

    def note_on(self, channel: int, note: int, velocity: int):
        if self.midi:
            self.midi.send_message([MIDI_NOTE_ON | channel, note & 0x7F, velocity & 0x7F])
        else:
            print(f"  NOTE_ON   ch={channel+1:02d}  note={note:03d}  vel={velocity:03d}")

    def note_off(self, channel: int, note: int):
        if self.midi:
            self.midi.send_message([MIDI_NOTE_OFF | channel, note & 0x7F, 0])
        else:
            print(f"  NOTE_OFF  ch={channel+1:02d}  note={note:03d}")

    def close(self):
        if self.midi:
            try:
                self.midi.close_port()
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────────
# NOTE-OFF SCHEDULER
# ─────────────────────────────────────────────────────────────────
def schedule_note_off(midi_out: MidiOut, channel: int, note: int, delay: float):
    def _off():
        time.sleep(delay)
        midi_out.note_off(channel, note)
    threading.Thread(target=_off, daemon=True).start()

# ─────────────────────────────────────────────────────────────────
# COMMAND DISPATCHER
# ─────────────────────────────────────────────────────────────────
def dispatch(cmd: str, midi_out: MidiOut):
    """
    Command grammar (same as v1 + OPEN_HAT_OFF):
        KICK_ON|<vel>       KICK_OFF|0
        SNARE_ON|<vel>      SNARE_OFF|0
        HAT_ON|<vel>        HAT_OFF|0
        OPEN_HAT_ON|<vel>   OPEN_HAT_OFF|0
        BASS_ON|<note>|<vel>
        BASS_OFF|0
        SYNTH_CHORD|<n1>,<n2>,...|<vel>|<long|short>
        ALL_OFF|0
    """
    parts  = cmd.strip().split("|")
    if not parts or not parts[0]:
        return
    action = parts[0]

    try:
        # ── KICK ────────────────────────────────────────────────
        if   action == "KICK_ON":    midi_out.note_on (DRUM_CHANNEL, KICK_NOTE,       int(parts[1]))
        elif action == "KICK_OFF":   midi_out.note_off(DRUM_CHANNEL, KICK_NOTE)

        # ── SNARE ───────────────────────────────────────────────
        elif action == "SNARE_ON":   midi_out.note_on (DRUM_CHANNEL, SNARE_NOTE,      int(parts[1]))
        elif action == "SNARE_OFF":  midi_out.note_off(DRUM_CHANNEL, SNARE_NOTE)

        # ── HI-HAT CLOSED ───────────────────────────────────────
        elif action == "HAT_ON":     midi_out.note_on (DRUM_CHANNEL, HAT_CLOSED_NOTE, int(parts[1]))
        elif action == "HAT_OFF":    midi_out.note_off(DRUM_CHANNEL, HAT_CLOSED_NOTE)

        # ── HI-HAT OPEN (scheduled auto-off) ────────────────────
        elif action == "OPEN_HAT_ON":
            vel = int(parts[1])
            midi_out.note_on(DRUM_CHANNEL, HAT_OPEN_NOTE, vel)
            # Open hat rings for a natural decay then cuts
            schedule_note_off(midi_out, DRUM_CHANNEL, HAT_OPEN_NOTE, 0.35)

        elif action == "OPEN_HAT_OFF":
            midi_out.note_off(DRUM_CHANNEL, HAT_OPEN_NOTE)

        # ── 808 BASS ────────────────────────────────────────────
        elif action == "BASS_ON":
            note = int(parts[1])
            vel  = int(parts[2])
            midi_out.note_on(BASS_CHANNEL, note, vel)
            schedule_note_off(midi_out, BASS_CHANNEL, note, BASS_DUR)

        elif action == "BASS_OFF":
            for n in range(24, 85):
                midi_out.note_off(BASS_CHANNEL, n)

        # ── SYNTH CHORDS ────────────────────────────────────────
        elif action == "SYNTH_CHORD":
            notes    = [int(n) for n in parts[1].split(",")]
            vel      = int(parts[2])
            duration = SYNTH_LONG_DUR if parts[3] == "long" else SYNTH_SHORT_DUR
            for note in notes:
                midi_out.note_on(SYNTH_CHANNEL, note, vel)
                schedule_note_off(midi_out, SYNTH_CHANNEL, note, duration)

        # ── ALL OFF (MIDI panic) ─────────────────────────────────
        elif action == "ALL_OFF":
            for ch in [DRUM_CHANNEL, BASS_CHANNEL, SYNTH_CHANNEL]:
                for note in range(128):
                    midi_out.note_off(ch, note)

    except (IndexError, ValueError) as e:
        print(f"[DISPATCH ERROR] cmd='{cmd}'  error={e}")


# ─────────────────────────────────────────────────────────────────
# TCP CLIENT MAIN LOOP
# ─────────────────────────────────────────────────────────────────
def run_client():
    midi_out = MidiOut()
    print("[CLIENT] MIDI output ready.")
    print("[CLIENT] Connecting to brains.py on localhost:8000 …")

    buffer = ""

    while True:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.connect(("localhost", 8000))
            print("[CLIENT] Connected — receiving IPC commands…\n")

            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    print("[CLIENT] Server closed connection.")
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        dispatch(line, midi_out)

        except ConnectionRefusedError:
            print("[CLIENT] brains.py not up yet — retrying in 1 s…")
            time.sleep(1)

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"[CLIENT] Connection lost ({e}) — retrying in 1 s…")
            time.sleep(1)

        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        time.sleep(1)


if __name__ == "__main__":
    run_client()
