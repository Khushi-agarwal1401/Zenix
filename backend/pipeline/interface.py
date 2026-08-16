from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class PipelineModule(ABC):
    """
    Abstract base class for all pipeline modules.
    """
    
    @abstractmethod
    async def process(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data and return the result.
        
        Args:
            input_data: The main input to process (e.g., user message).
            context: Shared context dictionary containing request_id, metadata, etc.
            
        Returns:
            A dictionary containing the processing result/next steps.
        """
        pass
