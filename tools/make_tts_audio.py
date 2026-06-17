# tools/make_tts_audio.py
"""Synthesize a SYNTHETIC test order to a WAV, for the Phase-6 real-mode E2E run.

Why synthetic TTS: the manual real-mode run (process-audio -> Whisper) needs an audio
file, but real dictated audio is biometric data and never enters this repo (see
docs/refs/legal-framework-anonymization.md). This produces a robotic TTS voice reading a
FICTIONAL order (no real client, site, or part numbers), so there is nothing to anonymize.

The output WAV lands in .tmp/ (gitignored) and is NOT committed. Uses the Windows built-in
System.Speech synthesizer via PowerShell -- no extra Python dependency, no API quota.

Usage:
    python tools/make_tts_audio.py                      # default text -> .tmp/real_e2e_order.wav
    python tools/make_tts_audio.py --out .tmp/x.wav
    python tools/make_tts_audio.py --text "Pedido 90001. Dos codos..."

The default text matches tests/realmode/test_real_e2e.py::DICTATED_ORDER so the manual
audio run and the automated text run exercise the same fictional order.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

# Keep in sync with tests/realmode/test_real_e2e.py::DICTATED_ORDER (fictional order).
DEFAULT_TEXT = (
    "Pedido 90001. Dos codos de media inox 304 noventa grados. "
    "Tres valvulas de bola de media de laton. "
    "Una junta de goma de una pulgada. "
    "Cinco metros de tubo DN20 inox."
)
DEFAULT_OUT = os.path.join(".tmp", "real_e2e_order.wav")

# PowerShell System.Speech: pick an installed Spanish voice if present, else the default.
_PS_TEMPLATE = r"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$es = $synth.GetInstalledVoices() |
      Where-Object {{ $_.VoiceInfo.Culture.Name -like 'es*' -and $_.Enabled }} |
      Select-Object -First 1
if ($es) {{ $synth.SelectVoice($es.VoiceInfo.Name) }}
$synth.SetOutputToWaveFile("{out}")
$synth.Speak(@'
{text}
'@)
$synth.Dispose()
"""


def synthesize(text: str, out_path: str) -> None:
    if sys.platform != "win32":
        raise SystemExit("[ERROR] This helper uses the Windows System.Speech synthesizer; "
                         "run it on Windows (or supply your own WAV).")

    out_abs = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)

    # @'...'@ is a literal here-string: no PowerShell interpolation of the order text.
    script = _PS_TEMPLATE.format(out=out_abs, text=text)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"[ERROR] TTS synthesis failed (exit {result.returncode}).")

    if not os.path.exists(out_abs):
        raise SystemExit("[ERROR] TTS reported success but no WAV was written.")
    size = os.path.getsize(out_abs)
    print(f"[OK] Wrote {out_abs} ({size} bytes)")
    print(f"[OK] Fictional order: {text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default=DEFAULT_TEXT,
                        help="Fictional order text to synthesize (no real identifiers).")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="Output WAV path (default: .tmp/real_e2e_order.wav).")
    args = parser.parse_args()
    synthesize(args.text, args.out)


if __name__ == "__main__":
    main()
