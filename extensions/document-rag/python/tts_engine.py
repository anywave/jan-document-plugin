#!/usr/bin/env python3
"""
TTS Engine for MOBIUS — Fully Offline
Uses Windows SAPI via pyttsx3. No internet required.
Outputs WAV audio files.
"""

import json
import os
import sys
import tempfile


def synthesize(text: str, voice_id: str, output_path: str, rate: int = 150, volume: float = 1.0) -> dict:
    """Synthesize speech to WAV file using SAPI."""
    import pyttsx3

    try:
        engine = pyttsx3.init()

        # Set voice if specified — prefer Desktop/SAPI voices over OneCore stubs
        if voice_id:
            voices = engine.getProperty('voices')
            matched = None
            vid = voice_id.lower()
            # First pass: prefer "Desktop" voices (real SAPI, always functional)
            for v in voices:
                if vid in v.name.lower() and "desktop" in v.name.lower():
                    matched = v
                    break
            # Second pass: any voice matching the name (OneCore, speech packs, etc.)
            if not matched:
                for v in voices:
                    if vid in v.id.lower() or vid in v.name.lower():
                        matched = v
                        break
            if matched:
                engine.setProperty('voice', matched.id)

        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)

        # Ensure parent directory exists
        parent = os.path.dirname(output_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            return {"success": True, "output_path": output_path, "size_bytes": size}
        else:
            return {"success": False, "error": "File was not created"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_voices() -> dict:
    """List all available SAPI voices on this machine."""
    import pyttsx3

    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        result = []
        for v in voices:
            # Extract locale from languages list or voice ID
            locale = ""
            if v.languages:
                lang = v.languages[0] if isinstance(v.languages[0], str) else ""
                locale = lang
            # Try to extract from voice name
            if "English (United States)" in v.name:
                locale = "en-US"
            elif "English (Australia)" in v.name:
                locale = "en-AU"
            elif "English (United Kingdom)" in v.name:
                locale = "en-GB"

            result.append({
                "id": v.id,
                "name": v.name,
                "gender": "Female" if v.gender and "female" in str(v.gender).lower() else "Male",
                "locale": locale,
            })

        # Also check OneCore voices that pyttsx3 might miss
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
            )
            i = 0
            existing_names = {r["name"] for r in result}
            while True:
                try:
                    token_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, token_name)
                    try:
                        attr_key = winreg.OpenKey(subkey, "Attributes")
                        name = winreg.QueryValueEx(attr_key, "Name")[0]
                        gender = winreg.QueryValueEx(attr_key, "Gender")[0]
                        if name not in existing_names:
                            result.append({
                                "id": f"OneCore:{token_name}",
                                "name": f"Microsoft {name} (OneCore)",
                                "gender": gender.capitalize(),
                                "locale": "en-US",
                            })
                    except WindowsError:
                        pass
                    i += 1
                except WindowsError:
                    break
        except Exception:
            pass

        engine.stop()
        return {"success": True, "voices": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_voice(voice_id: str, text: str = "Hello, this is a test of the speech synthesis engine.") -> dict:
    """Test a voice by speaking text directly (plays through speakers)."""
    import pyttsx3

    try:
        engine = pyttsx3.init()
        if voice_id:
            voices = engine.getProperty('voices')
            vid = voice_id.lower()
            # Prefer Desktop voices over OneCore stubs
            matched = None
            for v in voices:
                if vid in v.name.lower() and "desktop" in v.name.lower():
                    matched = v
                    break
            if not matched:
                for v in voices:
                    if vid in v.id.lower() or vid in v.name.lower():
                        matched = v
                        break
            if matched:
                engine.setProperty('voice', matched.id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: tts_engine.py <command> [args]"}))
        sys.exit(1)

    command = sys.argv[1]

    if command == "synthesize-stdin":
        # Read JSON payload from stdin — avoids arg sanitization and length limits
        payload = json.loads(sys.stdin.read())
        text = payload["text"]
        voice_id = payload.get("voice", "")
        output_path = payload["output_path"]
        rate = payload.get("rate", 150)
        volume = payload.get("volume", 1.0)
        result = synthesize(text, voice_id, output_path, rate, volume)
        print(json.dumps(result))

    elif command == "synthesize":
        if len(sys.argv) < 5:
            print(json.dumps({
                "success": False,
                "error": "Usage: tts_engine.py synthesize <text> <voice_id> <output_path> [rate] [volume]"
            }))
            sys.exit(1)
        text = sys.argv[2]
        voice_id = sys.argv[3]
        output_path = sys.argv[4]
        rate = int(sys.argv[5]) if len(sys.argv) > 5 else 150
        volume = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
        result = synthesize(text, voice_id, output_path, rate, volume)
        print(json.dumps(result))

    elif command == "list-voices":
        result = list_voices()
        print(json.dumps(result))

    elif command == "test":
        voice_id = sys.argv[2] if len(sys.argv) > 2 else ""
        text = sys.argv[3] if len(sys.argv) > 3 else "Hello, this is a test."
        result = test_voice(voice_id, text)
        print(json.dumps(result))

    else:
        print(json.dumps({"success": False, "error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
