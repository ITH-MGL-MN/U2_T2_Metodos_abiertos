# -*- coding: utf-8 -*-
import os
import yaml

ANCHO_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ_DIR = os.path.dirname(ANCHO_DIR)

def cargar_yaml(ruta_relativa):
    ruta_completa = os.path.join(RAIZ_DIR, ruta_relativa)
    with open(ruta_completa, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def obtener_configuracion():
    cfg = cargar_yaml('config/config.yaml')
    preguntas = cargar_yaml('config/preguntas.yaml')
    return cfg, preguntas
