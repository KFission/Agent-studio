"""
Guardrails AI — Default Configuration
Guards are created dynamically via the REST API from the backend.
This file provides the minimal startup config for the guardrails-api server.
"""
from guardrails import Guard

# No pre-configured guards — they are deployed on-demand via the API.
# The guardrails-api server starts with an empty guard registry.
# Guards are created/deleted via POST /guards and DELETE /guards/{name}
# from the JAI Agent OS backend when users deploy/undeploy them.
