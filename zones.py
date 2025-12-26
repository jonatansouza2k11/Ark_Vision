"""
zones.py

Define e gerencia zonas poligonais (áreas de interesse) em um frame de vídeo.
Cada zona é um polígono 2D (lista de pontos [x, y]) no sistema de coordenadas
da imagem redimensionada (por exemplo, 1200 x H).

Uso típico:
    from zones import ZoneManager

    zone_manager = ZoneManager(target_width=1200)
    zone_manager.draw_zones(frame)
    current_zone = zone_manager.point_zone(xc, yc)
"""

import numpy as np
import cv2


class ZoneManager:
    """
    Gerencia um conjunto de zonas poligonais nomeadas.

    Atributos:
        target_width (int): largura do frame redimensionado usado no projeto.
        zones (dict[str, np.ndarray]): dicionário nome -> polígono (Nx2 int32).
    """

    def __init__(self, target_width: int = 1200) -> None:
        """
        Inicializa o ZoneManager.

        Args:
            target_width: largura do frame que será usado para desenhar as zonas.
                          Deve ser a mesma usada no redimensionamento do vídeo.
        """
        self.target_width = target_width

        # Definição das zonas em coordenadas do frame redimensionado.
        # Cada zona é um polígono com vértices [x, y].
        # Ajuste esses pontos depois olhando o vídeo real.

        self.zones: dict[str, np.ndarray] = {
            # Zona grande na parte inferior (ex.: área de entrada / saída)
            "entrada": np.array(
                [
                    [50, 600],
                    [1150, 600],
                    [1150, 700],
                    [50, 700],
                ],
                dtype=np.int32,
            ),

            # Corredor vertical à esquerda
            "corredor_esq": np.array(
                [
                    [100, 100],
                    [300, 100],
                    [300, 550],
                    [100, 550],
                ],
                dtype=np.int32,
            ),

            # Faixas verticais simulando elevadores / torres
            "elevador_1": np.array(
                [
                    [350, 150],
                    [450, 150],
                    [450, 550],
                    [350, 550],
                ],
                dtype=np.int32,
            ),
            "elevador_2": np.array(
                [
                    [500, 150],
                    [600, 150],
                    [600, 550],
                    [500, 550],
                ],
                dtype=np.int32,
            ),
            "elevador_3": np.array(
                [
                    [650, 150],
                    [750, 150],
                    [750, 550],
                    [650, 550],
                ],
                dtype=np.int32,
            ),
            "elevador_4": np.array(
                [
                    [800, 150],
                    [900, 150],
                    [900, 550],
                    [800, 550],
                ],
                dtype=np.int32,
            ),
        }

    def draw_zones(self, frame) -> None:
        """
        Desenha todas as zonas no frame.

        Args:
            frame: imagem BGR (np.ndarray) onde as zonas serão desenhadas.
        """
        for name, poly in self.zones.items():
            # Desenha o contorno do polígono
            cv2.polylines(frame, [poly], isClosed=True, color=(255, 255, 0), thickness=2)
            # Escreve o nome da zona perto do primeiro vértice
            cv2.putText(
                frame,
                name,
                tuple(poly[0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 0),
                1,
            )

    def point_zone(self, xc: int, yc: int) -> str | None:
        """
        Retorna o nome da zona que contém o ponto (xc, yc), ou None se estiver fora.

        Args:
            xc: coordenada X do ponto (ex.: centro da bbox da pessoa).
            yc: coordenada Y do ponto.

        Returns:
            Nome da zona (str) se o ponto estiver dentro de algum polígono,
            ou None caso contrário.
        """
        for name, poly in self.zones.items():
            # pointPolygonTest > 0: dentro; =0: na borda; <0: fora
            if cv2.pointPolygonTest(poly, (float(xc), float(yc)), False) >= 0:
                return name
        return None
