from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Optional
import os
import tempfile
import httpx

def create_speech_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/speech", tags=["speech"])

    @router.post("/transcribe")
    async def transcribe_audio(
        audio: UploadFile = File(...),
        user=Depends(get_current_user)
    ):
        """
        تحويل الصوت إلى نص باستخدام OpenAI Whisper API
        """
        try:
            # قراءة الملف الصوتي
            audio_data = await audio.read()
            
            # حفظ مؤقت
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name

            try:
                # استخدام OpenAI Whisper
                openai_key = os.environ.get('OPENAI_DIRECT_KEY')
                if not openai_key:
                    raise HTTPException(status_code=500, detail="OpenAI key not configured")

                async with httpx.AsyncClient(timeout=30.0) as client:
                    with open(tmp_path, 'rb') as audio_file:
                        files = {
                            'file': (audio.filename or 'audio.webm', audio_file, 'audio/webm'),
                            'model': (None, 'whisper-1'),
                            'language': (None, 'ar')  # Arabic
                        }
                        
                        response = await client.post(
                            'https://api.openai.com/v1/audio/transcriptions',
                            headers={'Authorization': f'Bearer {openai_key}'},
                            files=files
                        )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get('text', '')
                    
                    # تسجيل في الإحصائيات
                    await db.speech_usage.insert_one({
                        'user_id': user['id'],
                        'duration': None,
                        'text_length': len(text),
                        'timestamp': None
                    })
                    
                    return {'ok': True, 'text': text}
                else:
                    error_msg = response.text
                    print(f"Whisper API error: {error_msg}")
                    raise HTTPException(status_code=500, detail="فشل تحويل الصوت")

            finally:
                # حذف الملف المؤقت
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            print(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
