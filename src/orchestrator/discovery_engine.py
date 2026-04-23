"""Motor de Descubrimiento Inteligente.

Sistema experto que guía al usuario con preguntas contextuales,
adaptativas y profesionales basadas en el tipo de proyecto.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
    """Tipos de proyecto detectables."""
    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    API_REST = "api_rest"
    DESKTOP_APP = "desktop_app"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    MICROSERVICE = "microservice"
    DATA_PIPELINE = "data_pipeline"
    ML_MODEL = "ml_model"
    UNKNOWN = "unknown"


class UserExpertiseLevel(Enum):
    """Nivel de experiencia técnica del usuario."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class DiscoveryContext:
    """Contexto acumulado durante el descubrimiento."""
    project_type: Optional[ProjectType] = None
    user_expertise: Optional[UserExpertiseLevel] = None
    project_name: Optional[str] = None
    main_goal: Optional[str] = None
    target_users: Optional[str] = None
    key_features: List[str] = None
    tech_preferences: Dict[str, str] = None
    constraints: Dict[str, Any] = None
    scope: Optional[str] = None
    
    def __post_init__(self):
        if self.key_features is None:
            self.key_features = []
        if self.tech_preferences is None:
            self.tech_preferences = {}
        if self.constraints is None:
            self.constraints = {}
    
    def completeness_score(self) -> float:
        """Calcula qué tan completo está el contexto (0-1)."""
        required_fields = [
            self.project_type is not None,
            self.main_goal is not None,
            self.target_users is not None,
            len(self.key_features) >= 3,
            bool(self.tech_preferences),
            self.scope is not None,
        ]
        return sum(required_fields) / len(required_fields)
    
    def is_ready(self) -> bool:
        """Verifica si hay suficiente información para proceder."""
        return self.completeness_score() >= 0.85


class DiscoveryEngine:
    """Motor inteligente de descubrimiento de requisitos."""
    
    # Palabras clave para detectar tipo de proyecto
    PROJECT_KEYWORDS = {
        ProjectType.WEB_APP: ["web", "sitio", "página", "website", "portal", "dashboard", "frontend"],
        ProjectType.MOBILE_APP: ["móvil", "mobile", "app", "android", "ios", "smartphone"],
        ProjectType.API_REST: ["api", "rest", "endpoint", "backend", "servicio", "microservicio"],
        ProjectType.DESKTOP_APP: ["escritorio", "desktop", "windows", "mac", "linux", "aplicación"],
        ProjectType.CLI_TOOL: ["cli", "terminal", "comando", "consola", "script"],
        ProjectType.LIBRARY: ["librería", "library", "paquete", "package", "módulo"],
        ProjectType.MICROSERVICE: ["microservicio", "microservice", "contenedor", "docker", "kubernetes"],
        ProjectType.DATA_PIPELINE: ["datos", "etl", "pipeline", "procesamiento", "batch"],
        ProjectType.ML_MODEL: ["machine learning", "ml", "ia", "modelo", "predicción", "clasificación"],
    }
    
    # Palabras clave para detectar nivel de experiencia
    EXPERTISE_KEYWORDS = {
        UserExpertiseLevel.BEGINNER: ["nuevo", "aprendiendo", "principiante", "básico", "simple"],
        UserExpertiseLevel.INTERMEDIATE: ["intermedio", "algo de experiencia", "conozco"],
        UserExpertiseLevel.ADVANCED: ["avanzado", "experiencia", "profesional"],
        UserExpertiseLevel.EXPERT: ["experto", "senior", "arquitecto", "años de experiencia"],
    }
    
    def __init__(self):
        self.context = DiscoveryContext()
    
    def detect_project_type(self, text: str) -> Optional[ProjectType]:
        """Detecta el tipo de proyecto basado en el texto del usuario."""
        text_lower = text.lower()
        
        scores = {}
        for proj_type, keywords in self.PROJECT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[proj_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return ProjectType.UNKNOWN
    
    def detect_expertise_level(self, text: str) -> Optional[UserExpertiseLevel]:
        """Detecta el nivel de experiencia del usuario."""
        text_lower = text.lower()
        
        for level, keywords in self.EXPERTISE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return level
        
        # Por defecto, asumir intermedio
        return UserExpertiseLevel.INTERMEDIATE
    
    def get_contextual_questions(self) -> List[str]:
        """Genera preguntas contextuales basadas en el estado actual."""
        questions = []
        
        # Fase 1: Identificar tipo de proyecto
        if self.context.project_type is None:
            questions.append(
                "Para empezar, ¿qué tipo de software quieres crear? "
                "(Por ejemplo: una aplicación web, una API, una app móvil, etc.)"
            )
            return questions
        
        # Fase 2: Objetivo principal
        if self.context.main_goal is None:
            questions.extend(self._get_goal_questions())
            return questions[:2]
        
        # Fase 3: Usuarios objetivo
        if self.context.target_users is None:
            questions.extend(self._get_user_questions())
            return questions[:2]
        
        # Fase 4: Funcionalidades clave
        if len(self.context.key_features) < 3:
            questions.extend(self._get_feature_questions())
            return questions[:2]
        
        # Fase 5: Preferencias técnicas
        if not self.context.tech_preferences:
            questions.extend(self._get_tech_questions())
            return questions[:2]
        
        # Fase 6: Alcance y restricciones
        if self.context.scope is None:
            questions.extend(self._get_scope_questions())
            return questions[:2]
        
        return []
    
    def _get_goal_questions(self) -> List[str]:
        """Preguntas sobre el objetivo según el tipo de proyecto."""
        base = "¿Cuál es el objetivo principal de "
        
        if self.context.project_type == ProjectType.WEB_APP:
            return [
                f"{base}tu aplicación web? ¿Qué problema específico resuelve para los usuarios?",
                "¿Es un sitio informativo, una plataforma interactiva, un e-commerce, o algo diferente?"
            ]
        elif self.context.project_type == ProjectType.API_REST:
            return [
                f"{base}tu API? ¿Qué datos o servicios va a exponer?",
                "¿Quién va a consumir esta API? ¿Aplicaciones internas, terceros, o ambos?"
            ]
        elif self.context.project_type == ProjectType.MOBILE_APP:
            return [
                f"{base}tu app móvil? ¿Qué necesidad cubre que no cubren otras apps?",
                "¿Necesita funcionar offline? ¿Usará funciones del dispositivo (cámara, GPS, etc.)?"
            ]
        elif self.context.project_type == ProjectType.DATA_PIPELINE:
            return [
                "¿Qué datos necesitas procesar y de dónde vienen?",
                "¿Cuál es el resultado esperado? ¿Reportes, dashboards, alimentar otro sistema?"
            ]
        elif self.context.project_type == ProjectType.ML_MODEL:
            return [
                "¿Qué problema quieres resolver con machine learning? ¿Predicción, clasificación, recomendación?",
                "¿Tienes datos históricos disponibles? ¿Cuántos registros aproximadamente?"
            ]
        else:
            return [
                f"{base}este proyecto? ¿Qué problema resuelve?",
                "¿Cómo sabrás que el proyecto es exitoso? ¿Qué métricas importan?"
            ]
    
    def _get_user_questions(self) -> List[str]:
        """Preguntas sobre usuarios objetivo."""
        if self.context.project_type == ProjectType.API_REST:
            return [
                "¿Quiénes son los desarrolladores que consumirán tu API? ¿Internos o externos?",
                "¿Necesitan documentación interactiva (Swagger/OpenAPI)?"
            ]
        elif self.context.project_type == ProjectType.CLI_TOOL:
            return [
                "¿Quién usará esta herramienta? ¿Desarrolladores, administradores de sistemas, usuarios finales?",
                "¿Qué nivel técnico tienen? ¿Necesitan ayuda detallada o comandos avanzados?"
            ]
        else:
            return [
                "¿Quiénes son los usuarios principales? Descríbelos (rol, experiencia técnica, necesidades)",
                "¿Cuántos usuarios concurrentes esperas? ¿10, 100, 1000, más?"
            ]
    
    def _get_feature_questions(self) -> List[str]:
        """Preguntas sobre funcionalidades clave."""
        count = len(self.context.key_features)
        
        if count == 0:
            return [
                "¿Cuáles son las 3-5 funcionalidades MÁS IMPORTANTES? (La razón de ser del proyecto)",
                "Si tuvieras que lanzar una versión mínima, ¿qué NO puede faltar?"
            ]
        elif count < 3:
            return [
                f"Perfecto, ya tengo {count} funcionalidad(es). ¿Qué más es esencial?",
                "¿Hay alguna integración crítica? (Pagos, autenticación, APIs externas, etc.)"
            ]
        else:
            return [
                "¿Los usuarios necesitan registrarse/iniciar sesión?",
                "¿Necesitas notificaciones? (Email, push, SMS, etc.)"
            ]
    
    def _get_tech_questions(self) -> List[str]:
        """Preguntas sobre preferencias técnicas."""
        if self.context.user_expertise in [UserExpertiseLevel.BEGINNER, UserExpertiseLevel.INTERMEDIATE]:
            return [
                "¿Tienes preferencia de lenguaje de programación? (Si no, te recomiendo según el proyecto)",
                "¿Necesitas que funcione en la nube o puede ser local?"
            ]
        else:
            return [
                "¿Qué stack tecnológico prefieres? (Lenguaje, framework, base de datos)",
                "¿Tienes restricciones de infraestructura? (Cloud provider, on-premise, híbrido)"
            ]
    
    def _get_scope_questions(self) -> List[str]:
        """Preguntas sobre alcance y restricciones."""
        return [
            "¿Es un prototipo/MVP para validar la idea, o algo para producción desde el inicio?",
            "¿Tienes fecha límite o restricciones de presupuesto importantes?"
        ]
    
    def generate_summary(self) -> str:
        """Genera un resumen ejecutivo del proyecto."""
        if not self.context.project_type:
            return ""
        
        summary_parts = []
        
        # Tipo y nombre
        proj_type_name = {
            ProjectType.WEB_APP: "aplicación web",
            ProjectType.MOBILE_APP: "aplicación móvil",
            ProjectType.API_REST: "API REST",
            ProjectType.DESKTOP_APP: "aplicación de escritorio",
            ProjectType.CLI_TOOL: "herramienta de línea de comandos",
            ProjectType.LIBRARY: "librería/paquete",
            ProjectType.MICROSERVICE: "microservicio",
            ProjectType.DATA_PIPELINE: "pipeline de datos",
            ProjectType.ML_MODEL: "modelo de machine learning",
        }.get(self.context.project_type, "proyecto de software")
        
        summary_parts.append(f"**Tipo:** {proj_type_name.title()}")
        
        if self.context.project_name:
            summary_parts.append(f"**Nombre:** {self.context.project_name}")
        
        # Objetivo
        if self.context.main_goal:
            summary_parts.append(f"**Objetivo:** {self.context.main_goal}")
        
        # Usuarios
        if self.context.target_users:
            summary_parts.append(f"**Usuarios:** {self.context.target_users}")
        
        # Funcionalidades
        if self.context.key_features:
            features_list = "\n".join(f"  - {f}" for f in self.context.key_features)
            summary_parts.append(f"**Funcionalidades clave:**\n{features_list}")
        
        # Tech stack
        if self.context.tech_preferences:
            tech_list = "\n".join(f"  - {k}: {v}" for k, v in self.context.tech_preferences.items())
            summary_parts.append(f"**Tecnologías:**\n{tech_list}")
        
        # Alcance
        if self.context.scope:
            summary_parts.append(f"**Alcance:** {self.context.scope}")
        
        return "\n\n".join(summary_parts)
    
    def get_tech_recommendations(self) -> Dict[str, str]:
        """Genera recomendaciones técnicas basadas en el tipo de proyecto."""
        if not self.context.project_type:
            return {}
        
        recommendations = {}
        
        if self.context.project_type == ProjectType.WEB_APP:
            recommendations = {
                "Frontend": "React + TypeScript (moderno, escalable, gran comunidad)",
                "Backend": "FastAPI (Python) o Express (Node.js) - rápidos y fáciles",
                "Base de datos": "PostgreSQL (robusto, gratuito, SQL completo)",
                "Hosting": "Vercel (frontend) + Railway/Render (backend) - deploy automático"
            }
        elif self.context.project_type == ProjectType.API_REST:
            recommendations = {
                "Framework": "FastAPI (Python) - documentación automática, async, type hints",
                "Base de datos": "PostgreSQL + SQLAlchemy ORM",
                "Autenticación": "JWT con OAuth2",
                "Documentación": "OpenAPI/Swagger automático con FastAPI"
            }
        elif self.context.project_type == ProjectType.MOBILE_APP:
            recommendations = {
                "Framework": "React Native (iOS + Android con un código) o Flutter",
                "Backend": "Firebase (sin servidor) o API REST propia",
                "Estado": "Redux o Context API",
                "Notificaciones": "Firebase Cloud Messaging"
            }
        elif self.context.project_type == ProjectType.DATA_PIPELINE:
            recommendations = {
                "Orquestación": "Apache Airflow o Prefect",
                "Procesamiento": "Pandas (pequeño) o PySpark (grande)",
                "Almacenamiento": "PostgreSQL o Data Warehouse (BigQuery, Snowflake)",
                "Visualización": "Metabase o Superset (open source)"
            }
        elif self.context.project_type == ProjectType.ML_MODEL:
            recommendations = {
                "Framework": "scikit-learn (clásico) o PyTorch/TensorFlow (deep learning)",
                "Experimentación": "Jupyter Notebooks + MLflow",
                "Deployment": "FastAPI + Docker",
                "Monitoreo": "Evidently AI o WhyLabs"
            }
        
        return recommendations
