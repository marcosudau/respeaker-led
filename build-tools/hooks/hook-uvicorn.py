from __future__ import annotations

# Keep the frozen service aligned with the explicit uvicorn.Config in
# src/interfaces/cli.py. The upstream hook collects optional protocol and
# reload backends that this project does not use, which creates noisy
# PyInstaller missing-module warnings.
hiddenimports = [
    "uvicorn.lifespan.on",
    "uvicorn.logging",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
]

excludedimports = [
    "uvicorn.loops.auto",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.websockets_sansio_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.supervisors.watchfilesreload",
    "uvicorn.workers",
]
