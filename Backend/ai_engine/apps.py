from django.apps import AppConfig


class AiEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_engine'
    verbose_name = 'AI Engine'

    def ready(self):
        """
        Called once when Django starts.

        Warm up the LangGraph checkpointer here so the first request doesn't
        pay the cost of initialising database connections and schema checks.

        The checkpointer creates tables automatically via Django migrations
        (handled by the langgraph-checkpoint-django package), so it is safe
        to import and instantiate at startup.
        """
        # Import lazily to avoid circular imports at boot time.
        # Import workflow.py (main Phase 3 graph) — NOT basic_workflow.py.
        try:
            from ai_engine.workflow import get_workflow_graph
            get_workflow_graph()
        except Exception:
            # If the database is not ready yet (e.g. running migrations), skip silently.
            # The next request will retry.
            pass
