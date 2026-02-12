import asyncio
import base64
import json
import random
import string
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts

app = FastAPI()

# Modeli RAM'e yükle (CPU)
print("?? Model Yükleniyor...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

async def generate_tts(text, lang_code):
    voice = "en-US-AriaNeural"
    if lang_code == "tr": voice = "tr-TR-AhmetNeural"
    elif lang_code == "de": voice = "de-DE-ConradNeural"
    elif lang_code == "fr": voice = "fr-FR-DeniseNeural"
    elif lang_code == "es": voice = "es-ES-ElviraNeural"
    
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
            
    return base64.b64encode(audio_data).decode('utf-8')

@app.get("/")
def read_root():
    return {"status": "GlobalTalk Backend Çal???yor!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_room = None
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "create_room":
                code = generate_room_code()
                my_lang = msg.get("lang", "tr")
                rooms[code] = [{"ws": websocket, "lang": my_lang}]
                current_room = code
                await websocket.send_json({"type": "created", "code": code})

            elif msg["type"] == "join_room":
                code = msg.get("code")
                my_lang = msg.get("lang", "en")
                if code in rooms:
                    rooms[code].append({"ws": websocket, "lang": my_lang})
                    current_room = code
                    await websocket.send_json({"type": "joined", "code": code})
                    # Partner'e haber ver
                    for user in rooms[code]:
                        if user["ws"] != websocket:
                            await user["ws"].send_json({"type": "partner_joined"})
                else:
                    await websocket.send_json({"type": "error", "message": "Oda Yok"})

            elif msg["type"] == "audio_chunk":
                if not current_room: continue

                # 1. Kaydet
                audio_bytes = base64.b64decode(msg["audio_data"])
                temp_filename = f"temp_{id(websocket)}.wav"
                with open(temp_filename, "wb") as f:
                    f.write(audio_bytes)

                # 2. Transcribe
                segments, _ = model.transcribe(temp_filename, beam_size=5)
                original_text = " ".join([s.text for s in segments])
                
                if os.path.exists(temp_filename): os.remove(temp_filename)
                if not original_text.strip(): continue

                # 3. Translate & TTS & Send
                room_users = rooms[current_room]
                for user in room_users:
                    target_ws = user["ws"]
                    target_lang = user["lang"]
                    
                    if target_ws == websocket:
                         await target_ws.send_json({
                            "type": "subtitle",
                            "sender": "me",
                            "text": original_text
                        })
                    else:
                        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(original_text)
                        audio_b64 = await generate_tts(translated_text, target_lang)
                        await target_ws.send_json({
                            "type": "subtitle",
                            "sender": "partner",
                            "text": translated_text,
                            "audio": audio_b64
                        })

    except WebSocketDisconnect:
        if current_room and current_room in rooms:
            rooms[current_room] = [u for u in rooms[current_room] if u["ws"] != websocket]
            if not rooms[current_room]: del rooms[current_room]