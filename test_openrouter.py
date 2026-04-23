"""Test de conexión con OpenRouter.

Verifica que la configuración de OpenRouter esté correcta.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

import os


def test_openrouter():
    """Prueba la conexión con OpenRouter."""
    print("=" * 80)
    print("🧪 Test de OpenRouter")
    print("=" * 80)
    
    # Verificar variables de entorno
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    provider = os.getenv("LLM_PROVIDER")
    model = os.getenv("LLM_MODEL")
    
    print("\n📋 Configuración:")
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    print(f"  API Base: {api_base}")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'NO CONFIGURADA'}")
    
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY no está configurada")
        return False
    
    if not api_base or "openrouter" not in api_base:
        print("\n⚠️ ADVERTENCIA: OPENAI_API_BASE no apunta a OpenRouter")
        print(f"   Actual: {api_base}")
        print(f"   Esperado: https://openrouter.ai/api/v1")
    
    if provider != "openai":
        print(f"\n⚠️ ADVERTENCIA: LLM_PROVIDER es '{provider}', debería ser 'openai' para OpenRouter")
    
    # Probar con Agno
    print("\n🔧 Probando con Agno...")
    
    try:
        from src.config.settings import get_settings, get_model
        
        settings = get_settings()
        print(f"\n✅ Settings cargados:")
        print(f"  Provider: {settings.llm_provider}")
        print(f"  Model: {settings.llm_model}")
        print(f"  API Base: {settings.openai_api_base}")
        
        # Crear modelo
        model = get_model()
        print(f"\n✅ Modelo creado: {type(model).__name__}")
        
        # Verificar que tenga base_url configurado
        if hasattr(model, 'client') and hasattr(model.client, 'base_url'):
            print(f"  Base URL: {model.client.base_url}")
        
        # Test simple
        print("\n🧪 Probando llamada simple...")
        from agno.agent import Agent
        
        test_agent = Agent(
            name="Test Agent",
            model=model,
            instructions=["Responde brevemente en español."]
        )
        
        response = test_agent.run("Di 'Hola desde OpenRouter'", stream=False)
        
        print(f"\n✅ Respuesta recibida:")
        print(f"  {response.content[:200]}...")
        
        print("\n🎉 ¡OpenRouter funciona correctamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_openrouter()
    sys.exit(0 if success else 1)
