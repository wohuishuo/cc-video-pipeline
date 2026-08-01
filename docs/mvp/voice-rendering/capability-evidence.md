# Voice Rendering capability evidence

Seven domain tests prove exact voice-policy parsing, Translation Manifest ordering, one active synthesis call, hash-bound clip publication, failed-clip isolation, successful checkpoint reuse, duplicate replay, input conflict, Edge argv construction, duration probing and public CLI behavior.

Live evidence on 2026-08-02 used `ru-RU-DmitryNeural` and `kk-KZ-DauletNeural`. The first service run completed three clips and failed one; the identical retry synthesized only the failed Russian clip and reused the other three. The final four clips total 23.232 seconds and the Voice Manifest SHA-256 is `ccbfd566073f1b548fe02a9eb01fedda6be5f6a77af37575f1e786b5db802d56`.
