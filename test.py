from ultralytics import YOLO
import cv2
import time

# ===================== CARREGAR MODELO =====================
print("[INFO] Carregando modelo YOLOv8n...")
model = YOLO("yolo_models\\yolov8n.pt", task="detect")

# ===================== CONFIGURAR WEBCAM =====================
print("[INFO] Abrindo webcam...")
cap = cv2.VideoCapture(0)  # 0 = webcam padrão

# Configurar resolução da webcam
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("[ERRO] Não foi possível abrir a webcam!")
    exit()

print("[✓] Webcam aberta com sucesso!")
print("[INFO] Pressione 'q' para sair do teste\n")

# ===================== PROCESSAR FRAMES =====================
frame_count = 0
start_time = time.time()

try:
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("[ERRO] Falha ao capturar frame")
            break
        
        frame_count += 1
        
        # Fazer detecção no frame
        results = model(frame, conf=0.5, verbose=False)
        
        # Desenhar resultados no frame
        annotated_frame = results[0].plot()
        
        # Mostrar FPS
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        
        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        # Contar detecções
        detections = len(results[0].boxes)
        cv2.putText(
            annotated_frame,
            f"Deteccoes: {detections}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        # Mostrar frame
        cv2.imshow("YOLO11 - Teste Webcam", annotated_frame)
        
        # Pressionar 'q' para sair
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[INFO] Saindo do teste...")
            break

except KeyboardInterrupt:
    print("\n[INFO] Teste interrompido pelo usuário")

finally:
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n[RESUMO]")
    print(f"  • Frames processados: {frame_count}")
    print(f"  • Tempo total: {elapsed_time:.2f}s")
    print(f"  • FPS médio: {frame_count / elapsed_time:.2f}")
    print("[✓] Teste finalizado!")
