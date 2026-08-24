This folder is intentionally empty.

PenFight Arena's sound effects (flick, collision, fall, countdown,
victory/defeat, UI clicks) are synthesized at runtime via the Web Audio API
in static/js/audio.js, rather than shipped as binary asset files. This keeps
the project a fully self-contained, dependency-free download.

If you'd like to swap in real audio files instead, drop them here and wire
them into static/js/audio.js (e.g. using <audio> elements or
AudioContext.decodeAudioData) in place of the synthesized tones.
