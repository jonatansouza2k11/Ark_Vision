# backend/app/api/video.py
"""
Rotas para streaming de vídeo YOLO
"""
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
import cv2
import time

router = APIRouter()

# Variável global para controlar o stream
video_generator = None


def generate_video_stream():
    """
    Gerador de frames do stream de vídeo
    Mock básico - depois você integra com seu yolo.py
    """
    # Por enquanto, vamos criar um stream de teste
    cap = cv2.VideoCapture(0)  # Webcam
    
    if not cap.isOpened():
        # Se não tiver webcam, criar frame preto de teste
        while True:
            # Frame preto 640x480
            frame = cv2.imread('placeholder.jpg') if os.path.exists('placeholder.jpg') else create_black_frame()
            
            # Adicionar texto
            cv2.putText(frame, 'YOLO Stream - Aguardando...',
                       (50, 240), cv2.FONT_HERSHEY_SIMPLEX,
                       0.7, (255, 255, 255), 2)
            
            # Converter para JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.1)  # 10 FPS
    else:
        while cap.isOpened():
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Aqui você pode adicionar a detecção YOLO
            # frame = yolo_detector.detect(frame)
            
            # Converter para JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        cap.release()


def create_black_frame():
    """Criar frame preto de teste"""
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    return frame


@router.get("/video_feed")
async def video_feed():
    """
    Endpoint de streaming de vídeo
    Retorna um stream MJPEG
    """
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/video_status")
async def video_status():
    """
    Status do stream de vídeo
    """
    return {
        "status": "online",
        "source": "webcam",
        "fps": 30
    }
