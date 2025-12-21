import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Add project root and src to path to resolve imports
# We need to go up two levels from netlify/functions/api.py to reach the root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
src_path = os.path.join(project_root, "src")

# Add paths if they are not already there
if project_root not in sys.path:
    sys.path.append(project_root)
if src_path not in sys.path:
    sys.path.append(src_path)

# Also try to add the parent of the project root to support 'NewsletterAiAgent.src...' imports
# This mimics the structure where the repo folder is treated as a package
parent_root = os.path.dirname(project_root)
if parent_root not in sys.path:
    sys.path.append(parent_root)

try:
    from mangum import Mangum
    from api.main import app
    
    handler = Mangum(app)
except Exception as e:
    logger.error(f"Failed to import app: {e}")
    raise
