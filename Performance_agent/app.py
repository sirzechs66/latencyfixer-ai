from fastapi import FastAPI
import os


from config import Config


# Dynamic import of routers and middleware based on API_VERSION
API_VERSION = Config.API_VERSION
middleware_mod = __import__(f"api.{API_VERSION}.middleware.cors", fromlist=["CORSSettings"])
error_mod = __import__(f"api.{API_VERSION}.middleware.error_handler", fromlist=["ErrorLoggerMiddleware"])
analyze_mod = __import__(f"api.{API_VERSION}.routes.analyze", fromlist=["router"])
health_mod = __import__(f"api.{API_VERSION}.routes.health", fromlist=["router"])
test_cases_mod = __import__(f"api.{API_VERSION}.routes.test_cases", fromlist=["router"])


app = FastAPI(
    title="LatencyFixer AI API",
    description="Performance latency analysis using LangGraph-based multi-stage agent",
    version="1.0.0"
)

middleware_mod.CORSSettings.apply_middleware(app, production=False)
app.add_middleware(error_mod.ErrorLoggerMiddleware)
app.include_router(analyze_mod.router)
app.include_router(health_mod.router)
app.include_router(test_cases_mod.router)

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    # Get host/port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))

    uvicorn.run(app, host=host, port=port)
