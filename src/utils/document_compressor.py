"""Compresor de Documentos para Optimización de Tokens.

Extrae solo las secciones esenciales de documentos largos para
reducir el uso de tokens sin perder información crítica.
"""

import re
from typing import Dict, List


def extract_requirements_summary(full_doc: str) -> str:
    """Extrae resumen ejecutivo de requisitos (reduce ~70% tokens).
    
    Args:
        full_doc: Documento completo de requisitos
        
    Returns:
        Resumen con solo info esencial
    """
    lines = full_doc.split('\n')
    summary_parts = []
    
    # Extraer solo secciones críticas
    in_executive = False
    in_functional = False
    in_non_functional = False
    
    rf_count = 0
    rnf_count = 0
    
    for line in lines:
        # Versión ejecutiva completa
        if 'VERSIÓN EJECUTIVA' in line or 'VERSION EJECUTIVA' in line:
            in_executive = True
            summary_parts.append(line)
            continue
        
        if in_executive:
            summary_parts.append(line)
            if 'VERSIÓN TÉCNICA' in line or 'VERSION TECNICA' in line:
                in_executive = False
                break
    
    # Extraer solo IDs y títulos de requisitos (no descripciones completas)
    for line in lines:
        if re.match(r'^RF-\d+:', line):
            rf_count += 1
            # Solo título, no descripción completa
            title = line.split(':')[1].strip() if ':' in line else line
            summary_parts.append(f"RF-{rf_count:03d}: {title[:80]}")
        elif re.match(r'^RNF-\d+:', line):
            rnf_count += 1
            title = line.split(':')[1].strip() if ':' in line else line
            summary_parts.append(f"RNF-{rnf_count:03d}: {title[:80]}")
    
    return '\n'.join(summary_parts)


def extract_design_essentials(full_doc: str) -> str:
    """Extrae solo lo esencial del diseño para implementación (reduce ~60% tokens).
    
    Args:
        full_doc: Documento completo de diseño
        
    Returns:
        Solo stack, arquitectura y modelo de datos
    """
    lines = full_doc.split('\n')
    essential_parts = []
    
    # Secciones que SÍ necesita implementación
    capture_sections = [
        'Stack Tecnológico',
        'STACK TECNOLOGICO',
        'Patrón Arquitectura',
        'PATRON ARQUITECTURA', 
        'Componentes',
        'COMPONENTES',
        'Modelo Datos',
        'MODELO DATOS',
        'Contratos API',
        'CONTRATOS API',
        'Arquitectura Seguridad',
        'ARQUITECTURA SEGURIDAD'
    ]
    
    capturing = False
    section_lines = 0
    
    for line in lines:
        # Detectar inicio de sección relevante
        if any(section in line for section in capture_sections):
            capturing = True
            section_lines = 0
            essential_parts.append(line)
            continue
        
        # Capturar contenido de sección relevante
        if capturing:
            section_lines += 1
            essential_parts.append(line)
            
            # Detener después de capturar suficiente de cada sección
            if section_lines > 30 or (line.startswith('##') and section_lines > 5):
                capturing = False
    
    return '\n'.join(essential_parts)


def compress_for_validation(requirements_doc: str, design_doc: str, 
                            implementation_summary: str) -> str:
    """Comprime documentos para validación (reduce ~50% tokens).
    
    Args:
        requirements_doc: Documento de requisitos
        design_doc: Documento de diseño
        implementation_summary: Resumen de implementación
        
    Returns:
        Documento comprimido con info esencial para validación
    """
    compressed = []
    
    # Requisitos: solo IDs y prioridades
    compressed.append("# REQUISITOS A VALIDAR\n")
    for line in requirements_doc.split('\n'):
        if re.match(r'^RF-\d+:', line) or re.match(r'^RNF-\d+:', line):
            # Solo ID y título
            parts = line.split(':')
            if len(parts) >= 2:
                compressed.append(f"{parts[0]}: {parts[1][:60]}")
    
    # Diseño: solo decisiones de seguridad
    compressed.append("\n# DECISIONES DE SEGURIDAD\n")
    in_security = False
    for line in design_doc.split('\n'):
        if 'Seguridad' in line or 'SEGURIDAD' in line:
            in_security = True
        elif line.startswith('##') and in_security:
            in_security = False
        
        if in_security:
            compressed.append(line)
    
    # Implementación: solo lista de archivos
    compressed.append("\n# ARCHIVOS IMPLEMENTADOS\n")
    compressed.append(implementation_summary)
    
    return '\n'.join(compressed)


def get_compression_stats(original: str, compressed: str) -> Dict[str, int]:
    """Calcula estadísticas de compresión.
    
    Args:
        original: Documento original
        compressed: Documento comprimido
        
    Returns:
        Dict con tokens originales, comprimidos y % reducción
    """
    # Estimación aproximada: 1 token ≈ 4 caracteres
    original_tokens = len(original) // 4
    compressed_tokens = len(compressed) // 4
    reduction_pct = int((1 - compressed_tokens / original_tokens) * 100) if original_tokens > 0 else 0
    
    return {
        'original_tokens': original_tokens,
        'compressed_tokens': compressed_tokens,
        'reduction_percent': reduction_pct,
        'tokens_saved': original_tokens - compressed_tokens
    }
