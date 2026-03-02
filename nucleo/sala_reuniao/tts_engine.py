"""
TTS Engine — Suporte a múltiplos provedores
Prioridade: ElevenLabs > Gemini 2.5 Flash > OpenAI
"""
import os, base64, logging, httpx, struct, wave, io
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.tts")

# ── Vozes por provedor ───────────────────────────────────────────

# ElevenLabs — vozes premium multilingual (melhor suporte ao português)
VOZES_ELEVENLABS = {
    "lucas":   "pNInz6obpgDQGcFmaJgB",  # Adam — masculino profissional, versátil
    "pedro":   "TxGEqnHWrfWFTfGW9XjX",  # Josh — masculino sério, grave
    "rafael":  "ErXwobaYiN019PkySvjV",  # Antoni — masculino jovem, dinâmico
    "ze":      "VR6AewLTigWG4xSOukaG",  # Arnold — masculino motivador, forte
    "beto":    "yoZ06aMxZJJ28mfd3POQ",  # Sam — masculino direto, claro
    "diana":   "EXAVITQu4vr4xnSDxMaL",  # Sarah — feminina articulada, natural
    "mariana": "MF3mGyEYCl7XYWbV9V6O",  # Elli — feminina jovem, expressiva
    "carla":   "21m00Tcm4TlvDq8ikWAM",  # Rachel — feminina executiva, calma
    "ana":     "AZnzlk1XvdvUeBnXmlld",  # Domi — feminina empática, suave
    "dani":    "zrHiDhphv9ZnVXBqCLjz",  # Glinda — feminina analítica, precisa
}

# Gemini TTS — vozes disponíveis no preview
VOZES_GEMINI = {
    "lucas":   "Charon",    # masculino, confiante
    "pedro":   "Fenrir",    # masculino, sério
    "rafael":  "Puck",      # masculino, jovem/energético
    "ze":      "Orus",      # masculino, motivador
    "beto":    "Fenrir",    # masculino, direto
    "diana":   "Aoede",     # feminina, articulada
    "mariana": "Leda",      # feminina, expressiva
    "carla":   "Aoede",     # feminina, executiva
    "ana":     "Leda",      # feminina, empática
    "dani":    "Kore",      # feminina, analítica
}

# OpenAI — fallback
VOZES_OPENAI = {
    "lucas": "onyx", "pedro": "echo", "rafael": "fable",
    "ze": "alloy", "beto": "echo",
    "diana": "nova", "mariana": "shimmer", "carla": "nova",
    "ana": "shimmer", "dani": "nova",
}

# Estilo de voz por agente para Gemini (usando style prompts)
ESTILOS_GEMINI = {
    "lucas":   "Fala como CEO jovem de startup brasileira. Direto, confiante, sem enrolação.",
    "pedro":   "Fala como CFO analítico. Tom sério mas acessível, focado em números.",
    "rafael":  "Fala como CPO empolgado com produto. Jovem, energético, orientado ao usuário.",
    "ze":      "Fala como coach executivo. Motivador, direto, corta o que não importa.",
    "beto":    "Fala como especialista em eficiência. Objetivo, prático, sem drama.",
    "diana":   "Fala como analista de mercado curiosa. Animada quando vê oportunidade.",
    "mariana": "Fala como CMO criativa. Expressiva, data-driven, confiante.",
    "carla":   "Fala como COO executiva. Firme, prática, focada em execução.",
    "ana":     "Fala como CHRO humana. Empática mas direta, focada em pessoas.",
    "dani":    "Fala como analista de dados. Clara, precisa, fala com base em evidência.",
}

# ── Helpers ──────────────────────────────────────────────────────

def pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> bytes:
    """Converte PCM raw para WAV em memória."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()

# ── ElevenLabs TTS ───────────────────────────────────────────────
async def tts_elevenlabs(texto: str, agente: str) -> bytes | None:
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return None
    voice_id = VOZES_ELEVENLABS.get(agente, VOZES_ELEVENLABS["lucas"])
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": texto[:500],
                    "model_id": "eleven_turbo_v2_5",  # mais rápido + alta qualidade — conta paga
                    "voice_settings": {
                        "stability": 0.4,
                        "similarity_boost": 0.85,
                        "style": 0.5,
                        "use_speaker_boost": True
                    }
                }
            )
            if r.status_code == 200:
                logger.info(f"✅ ElevenLabs TTS ok — {agente}")
                return r.content
            elif r.status_code in (401, 429):
                logger.warning(f"ElevenLabs quota/auth {r.status_code} — caindo para Gemini")
                return None
            else:
                logger.warning(f"ElevenLabs erro {r.status_code}: {r.text[:100]}")
                return None
    except Exception as e:
        logger.error(f"ElevenLabs exception: {e}")
        return None

# ── Gemini TTS ───────────────────────────────────────────────────
async def tts_gemini(texto: str, agente: str) -> bytes | None:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return None
    voice = VOZES_GEMINI.get(agente, "Charon")
    estilo = ESTILOS_GEMINI.get(agente, "")
    
    prompt = f"{estilo}\n\nFale o seguinte texto em português brasileiro:\n{texto[:500]}"
    
    try:
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": voice}
                            }
                        }
                    }
                }
            )
            if r.status_code == 200:
                data = r.json()
                audio_data = data["candidates"][0]["content"]["parts"][0].get("inlineData", {}).get("data")
                if audio_data:
                    # Gemini retorna PCM — converter para WAV
                    pcm = base64.b64decode(audio_data)
                    wav = pcm_to_wav_bytes(pcm)
                    logger.info(f"✅ Gemini TTS ok — {agente} ({voice})")
                    return wav
            logger.warning(f"Gemini TTS erro {r.status_code}: {r.text[:150]}")
            return None
    except Exception as e:
        logger.error(f"Gemini TTS exception: {e}")
        return None

# ── OpenAI TTS (fallback) ─────────────────────────────────────────
async def tts_openai(texto: str, agente: str) -> bytes | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    voz = VOZES_OPENAI.get(agente, "alloy")
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "tts-1", "input": texto[:500], "voice": voz}
            )
            if r.status_code == 200:
                logger.info(f"✅ OpenAI TTS ok — {agente} ({voz})")
                return r.content
            return None
    except Exception as e:
        logger.error(f"OpenAI TTS exception: {e}")
        return None

# ── Engine principal com fallback ────────────────────────────────
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "auto")  # auto | elevenlabs | gemini | openai

async def gerar_audio_multi(texto: str, agente: str) -> str | None:
    """
    Gera áudio com fallback automático.
    Retorna base64 ou None.
    Prioridade: ElevenLabs > Gemini > OpenAI
    """
    audio_bytes = None

    if TTS_PROVIDER == "elevenlabs":
        audio_bytes = await tts_elevenlabs(texto, agente)
    elif TTS_PROVIDER == "gemini":
        audio_bytes = await tts_gemini(texto, agente)
    elif TTS_PROVIDER == "openai":
        audio_bytes = await tts_openai(texto, agente)
    else:  # auto — tenta pela ordem de qualidade
        if os.getenv("ELEVENLABS_API_KEY"):
            audio_bytes = await tts_elevenlabs(texto, agente)
        if not audio_bytes and os.getenv("GOOGLE_API_KEY"):
            audio_bytes = await tts_gemini(texto, agente)
        if not audio_bytes and os.getenv("OPENAI_API_KEY"):
            audio_bytes = await tts_openai(texto, agente)

    if audio_bytes:
        return base64.b64encode(audio_bytes).decode()
    return None
