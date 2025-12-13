from langchain.tools import tool
import speech_recognition as sr
from pydub import AudioSegment
import os


@tool
def transcribe_audio(file_path: str) -> str:
    """
    Transcribe an MP3 or WAV audio file into text using Google's Web Speech API.

    Args:
        file_path (str): Path to the input audio file (.mp3 or .wav).

    Returns:
        str: The transcribed text from the audio.

    Notes:
        - MP3 files are automatically converted to WAV.
        - Requires `pydub` and `speech_recognition` packages.
        - Uses Google's free recognize_google() API (requires internet).
    """
    # Try GenAI-based transcription if available (preferred). Do NOT hardcode API keys;
    # use the environment variable GOOGLE_API_KEY or GEMINI_API_KEY.
    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        genai = None

    base = __import__("shared_store").current_q_folder or "LLMFiles"
    file_path = os.path.join(base, file_path)

    # If genai is available and an API key is set, use it
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if genai and api_key:
        try:
            genai.configure(api_key=api_key)
            model_name = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
            
            # Upload file and request transcription
            myfile = genai.upload_file(file_path)
            model = genai.GenerativeModel(model_name)
            prompt = "Transcribe this audio file exactly. Output only the transcription text."
            result = model.generate_content([myfile, prompt])
            # result.text may hold the transcription depending on SDK version
            transcription = getattr(result, "text", None) or str(result)
            return transcription
        except Exception as e:
            # Fall back to local transcription on any genai error
            print(f"genai transcription failed, falling back: {e}")

    # Fallback: local speech_recognition-based transcription
    try:
        final_path = file_path
        if file_path.lower().endswith(".mp3"):
            sound = AudioSegment.from_mp3(file_path)
            final_path = file_path.replace(".mp3", ".wav")
            sound.export(final_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(final_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)

        # If we converted the file, remove temp wav
        if final_path != file_path and os.path.exists(final_path):
            os.remove(final_path)

        return text
    except Exception as e:
        return f"Error occurred: {e}"
