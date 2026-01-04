"""
video.py

Router FastAPI para endpoints de vídeo/streaming YOLO.
Endpoints: stream, status, start, stop, pause, detections.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from jose import JWTError, jwt

from ..core.security import get_current_user
from ..core.config import settings
from ..core.video_processor import video_processor
from ..schemas.video import (
    VideoStatusSchema,
    VideoControlResponse,
    DetectionsListSchema,
    ZoneStatsSchema
)
from ..schemas.user import UserResponse

router = APIRouter()


# =========================
# HELPER: Validar token via query param
# =========================

async def verify_token_from_query(token: Optional[str] = Query(None)):
    """
    Valida token JWT recebido via query parameter (?token=xxx).
    
    Args:
        token: Token JWT na URL
        
    Returns:
        dict: Payload do token decodificado
        
    Raises:
        HTTPException: Se token inválido ou ausente
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido. Use ?token=SEU_TOKEN na URL"
        )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


# =========================
# VIDEO STREAM (SEGURO!)
# =========================

@router.get(
    "/stream",
    summary="Video Stream MJPEG",
    description="""
    Stream de vídeo MJPEG em tempo real com detecções YOLO.
    
    **Features:**
    - Detecções de pessoas com YOLO
    - Tracking com BoT-SORT
    - Zonas poligonais desenhadas
    - FPS em tempo real
    - IDs de tracking
    
    **Autenticação:**
    Envie o token JWT como query parameter:
    
    ```html
    <img src="http://localhost:8000/api/v1/video/stream?token=SEU_TOKEN_AQUI" />
    ```
    
    **Obter token:**
    1. Faça login em `/api/v1/auth/login`
    2. Copie o `access_token`
    3. Use na URL: `?token=ACCESS_TOKEN`
    
    **Segurança:**
    - ✅ Requer token JWT válido
    - ✅ Funciona em navegadores e tags HTML
    - ✅ Token expira automaticamente
    """
)
async def stream_video(token_data: dict = Depends(verify_token_from_query)):
    """
    Endpoint de streaming MJPEG com autenticação via query parameter.
    
    Args:
        token_data: Dados do token JWT validado
    
    Returns:
        StreamingResponse: Video stream multipart/x-mixed-replace
    """
    try:
        # Inicializa se necessário
        if not video_processor._initialized:
            success = await video_processor.initialize()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Não foi possível inicializar o sistema de vídeo"
                )
        
        # Inicia stream se não estiver rodando
        if not video_processor.yolo or not video_processor.yolo.is_live():
            await video_processor.start_stream()
        
        # Retorna generator
        return StreamingResponse(
            video_processor.get_frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao iniciar stream: {str(e)}"
        )


# =========================
# VIDEO STATUS
# =========================

@router.get(
    "/status",
    response_model=VideoStatusSchema,
    summary="Get Video Status",
    description="""
    Obtém status completo do sistema de vídeo em tempo real.
    
    **Retorna:**
    - Estado do sistema (running/paused/stopped)
    - FPS atual e média
    - Contadores de detecção (dentro/fora da zona)
    - Estatísticas de zonas
    - Uso de memória
    - Preset ativo
    
    **Requer:** Token JWT válido
    """
)
async def get_video_status(
    force_refresh: bool = False,
    current_user: UserResponse = Depends(get_current_user)
) -> VideoStatusSchema:
    """
    Obtém status do sistema de vídeo.
    
    Args:
        force_refresh: Força atualização do cache (default: False)
        current_user: Usuário autenticado (via JWT)
        
    Returns:
        VideoStatusSchema: Status completo do sistema
    """
    status_dict = await video_processor.get_status(force_refresh=force_refresh)
    return VideoStatusSchema(**status_dict)


# =========================
# VIDEO CONTROL
# =========================

@router.post(
    "/start",
    response_model=VideoControlResponse,
    summary="Start Video Stream",
    description="""
    Inicia o processamento de vídeo e detecção YOLO.
    
    **Ações:**
    - Carrega configurações do banco
    - Inicializa modelo YOLO
    - Abre fonte de vídeo (webcam/RTSP)
    - Inicia tracking
    
    **Requer:** Token JWT válido (admin ou user)
    """
)
async def start_video(
    current_user: UserResponse = Depends(get_current_user)
) -> VideoControlResponse:
    """
    Inicia o stream de vídeo.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        VideoControlResponse: Resultado da operação
    """
    result = await video_processor.start_stream()
    return VideoControlResponse(**result)


@router.post(
    "/stop",
    response_model=VideoControlResponse,
    summary="Stop Video Stream",
    description="""
    Para o processamento de vídeo.
    
    **Ações:**
    - Para stream MJPEG
    - Libera câmera
    - Finaliza gravações ativas
    - Limpa cache PyTorch
    - Executa garbage collection
    
    **Requer:** Token JWT válido (admin ou user)
    """
)
async def stop_video(
    current_user: UserResponse = Depends(get_current_user)
) -> VideoControlResponse:
    """
    Para o stream de vídeo.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        VideoControlResponse: Resultado da operação
    """
    result = await video_processor.stop_stream()
    return VideoControlResponse(**result)


@router.post(
    "/pause",
    response_model=VideoControlResponse,
    summary="Toggle Pause",
    description="""
    Alterna entre pausado e em execução.
    
    **Estados:**
    - `running` → `paused`: Congela frame atual
    - `paused` → `running`: Retoma processamento
    
    **Nota:** Câmera permanece ativa durante pausa.
    
    **Requer:** Token JWT válido
    """
)
async def toggle_pause_video(
    current_user: UserResponse = Depends(get_current_user)
) -> VideoControlResponse:
    """
    Alterna pausa do stream.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        VideoControlResponse: Resultado da operação
    """
    result = await video_processor.toggle_pause()
    return VideoControlResponse(**result)


# =========================
# DETECTIONS
# =========================

@router.get(
    "/detections",
    response_model=DetectionsListSchema,
    summary="Get Active Detections",
    description="""
    Lista todas as pessoas detectadas atualmente.
    
    **Para cada detecção:**
    - ID único do tracker
    - Status (IN/OUT da zona)
    - Tempo fora da zona
    - Índice da zona (-1 se fora)
    - Estado de gravação
    - Última detecção (timestamp)
    
    **Uso:**
    ```javascript
    // Polling a cada 500ms
    setInterval(async () => {
        const res = await fetch('/api/v1/video/detections');
        const data = await res.json();
        console.log(`${data.total} pessoas detectadas`);
    }, 500);
    ```
    
    **Requer:** Token JWT válido
    """
)
async def get_detections(
    current_user: UserResponse = Depends(get_current_user)
) -> DetectionsListSchema:
    """
    Obtém lista de detecções ativas.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        DetectionsListSchema: Lista de detecções
    """
    result = await video_processor.get_detections()
    return DetectionsListSchema(**result)


# =========================
# ZONES
# =========================

@router.get(
    "/zones",
    response_model=List[ZoneStatsSchema],
    summary="Get Zone Statistics",
    description="""
    Obtém estatísticas em tempo real de todas as zonas.
    
    **Para cada zona:**
    - Nome e modo (GENERIC, ENTRY, EXIT, etc)
    - Contagem de pessoas atual
    - Tempo vazia (se aplicável)
    - Tempo cheia (se aplicável)
    - Estado (OK, EMPTY_LONG, FULL_LONG)
    
    **Estados:**
    - `OK`: Funcionamento normal
    - `EMPTY_LONG`: Vazia há muito tempo
    - `FULL_LONG`: Cheia há muito tempo
    
    **Requer:** Token JWT válido
    """
)
async def get_zone_stats(
    current_user: UserResponse = Depends(get_current_user)
) -> List[ZoneStatsSchema]:
    """
    Obtém estatísticas das zonas.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        List[ZoneStatsSchema]: Lista de estatísticas por zona
    """
    status = await video_processor.get_status(force_refresh=True)
    zones = status.get("zones", [])
    return [ZoneStatsSchema(**z) for z in zones]


# =========================
# HEALTH CHECK
# =========================

@router.get(
    "/health",
    summary="Video System Health",
    description="""
    Verifica saúde do sistema de vídeo.
    
    **Checks:**
    - Sistema inicializado?
    - Modelo YOLO carregado?
    - Câmera acessível?
    - Memória disponível?
    
    **Não requer autenticação** (útil para monitoramento externo)
    """
)
async def health_check():
    """
    Health check do sistema de vídeo.
    
    Returns:
        dict: Status de saúde
    """
    try:
        is_initialized = video_processor._initialized
        
        if not is_initialized:
            return {
                "status": "not_initialized",
                "healthy": False,
                "message": "Sistema de vídeo não inicializado"
            }
        
        status = await video_processor.get_status(force_refresh=False)
        
        return {
            "status": "healthy",
            "healthy": True,
            "system_status": status.get("system_status"),
            "fps": status.get("fps"),
            "memory_mb": status.get("memory_mb"),
            "message": "Sistema operacional"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "message": f"Erro: {str(e)}"
        }
