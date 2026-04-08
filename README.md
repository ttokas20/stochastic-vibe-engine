# Stochastic Vibe Engine

A live, generative trap music engine. Instead of looping a fixed pattern, it uses **Markov chains and probabilistic sequencing** to produce beats that breathe — subtly different every time, the way a real musician plays.

## How it works

Three components talk to each other:

** `logic.py` — The Brain**  
Runs a drift-free 16th-note clock and generates beat events in real-time. Each instrument has its own probability model:
- **Kick**: position-weighted probability tables per artist
- **Hi-hats**: Markov chain transitions (closed → open → roll → ghost) that evolve bar-by-bar
- **Chords + pads**: phrase sequences that change every 4 bars
- **808 bass**: triggered alongside kick hits, root note pulled from the chord phrase

Two artist modes shape the overall feel:
- `travis` — rigid, bouncy, high kick density
- `don` — laid-back swing, sparse kicks, ghost-heavy hats

**`receiver.py` — The MIDI Client**  
Connects to the brain over TCP, receives IPC command strings, and translates them into MIDI note-on/off messages. Routes drums to ch.10, bass to ch.1, synth to ch.2. Works with any DAW or virtual instrument via a loopback MIDI port.

*`control.html` — The Live UI*
A browser-based control surface. Adjust BPM, switch artist DNA, change arrangement section (intro / verse / drop / chorus), and mute/unmute individual channels in real-time. Talks to the brain via a lightweight HTTP server.

## Architecture

```
control.html  →  HTTP POST  →  logic.py (port 8001)
                                    ↓  TCP stream
                               receiver.py (port 8000)
                                    ↓
                              MIDI output → DAW / synth
```

## Setup

```bash
pip install python-rtmidi

# Start the MIDI client first
python receiver.py

# Then start the brain
python logic.py

# Open control.html in a browser
```

A virtual MIDI loopback port is required (IAC Driver on macOS, loopMIDI on Windows) unless your DAW creates one automatically.

## Dependencies

- Python 3.8+
- `python-rtmidi`
- Any browser (for the control UI)
