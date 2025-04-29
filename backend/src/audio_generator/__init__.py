from .text_to_speech_google import GoogleTextToSpeech
from .text_to_speech_volcano import VolcanoTextToSpeech
from .language_router_tts import LanguageRouterTTS

# 为了保持与旧代码兼容，可以设置默认TTS为LanguageRouterTTS
TTS = LanguageRouterTTS

__all__ = ['GoogleTextToSpeech'] 