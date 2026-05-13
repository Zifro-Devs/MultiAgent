"""Módulo de prompts especializados por tipo de stack.

Este paquete contiene los prompts de sistema para cada agente, organizados
por tipo de stack técnico. El detector de stack selecciona el prompt
apropiado para maximizar la calidad del código generado.

Arquitectura:
- base.py         — Prompts base compartidos (mentalidad, estándares globales)
- analysis.py     — Prompts del agente de análisis (con pocos-shots)
- design.py       — Prompts del agente de diseño (con Mermaid + contratos)
- backend.py      — Prompts especializados en backend por framework
- frontend.py     — Prompts especializados en frontend por framework
- fullstack.py    — Prompts para proyectos fullstack coordinados
- mobile.py       — Prompts para apps móviles (RN, Flutter)
- cli.py          — Prompts para herramientas de línea de comandos
- data.py         — Prompts para pipelines de datos y ML
- testing.py      — Prompts del agente de testing (TDD)
- validation.py   — Prompts del agente de validación (auditoría)
- documentation.py — Prompts del agente de documentación
"""

from src.agents.prompts.selector import select_implementation_prompt, select_testing_prompt

__all__ = ["select_implementation_prompt", "select_testing_prompt"]
