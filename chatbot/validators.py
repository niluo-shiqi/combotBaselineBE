"""
Input validation for the Combot Backend application.
Provides comprehensive validation for all user inputs and API requests.
"""

import re
from typing import Dict, Any, Optional, List
from .constants import (
    VALIDATION_RULES, PROBLEM_TYPES, BRAND_TYPES, THINK_LEVELS, 
    FEEL_LEVELS, CONVERSATION_INDICES, RESPONSE_TYPES
)
from .exceptions import ValidationError


class InputValidator:
    """Centralized input validation for the application."""
    
    @staticmethod
    def validate_message(message: str, field_name: str = "message") -> str:
        """
        Validate user message input.
        
        Args:
            message: The message to validate
            field_name: Name of the field for error reporting
            
        Returns:
            str: Validated message
            
        Raises:
            ValidationError: If validation fails
        """
        if not message:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=message
            )
        
        if not isinstance(message, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=message
            )
        
        if len(message) > VALIDATION_RULES['MAX_MESSAGE_LENGTH']:
            raise ValidationError(
                f"{field_name} is too long (max {VALIDATION_RULES['MAX_MESSAGE_LENGTH']} characters)",
                field=field_name,
                value=len(message)
            )
        
        # Remove excessive whitespace
        message = re.sub(r'\s+', ' ', message.strip())
        
        if not message:
            raise ValidationError(
                f"{field_name} cannot be empty after trimming",
                field=field_name,
                value=message
            )
        
        return message
    
    @staticmethod
    def validate_conversation_index(index: Any, field_name: str = "conversation_index") -> int:
        """
        Validate conversation index.
        
        Args:
            index: The index to validate
            field_name: Name of the field for error reporting
            
        Returns:
            int: Validated index
            
        Raises:
            ValidationError: If validation fails
        """
        if index is None:
            raise ValidationError(
                f"{field_name} is required",
                field=field_name,
                value=index
            )
        
        try:
            index = int(index)
        except (ValueError, TypeError):
            raise ValidationError(
                f"{field_name} must be an integer",
                field=field_name,
                value=index
            )
        
        if index < 0:
            raise ValidationError(
                f"{field_name} must be non-negative",
                field=field_name,
                value=index
            )
        
        return index
    
    @staticmethod
    def validate_time_spent(time_spent: Any, field_name: str = "time_spent") -> int:
        """
        Validate time spent in conversation.
        
        Args:
            time_spent: The time to validate
            field_name: Name of the field for error reporting
            
        Returns:
            int: Validated time spent
            
        Raises:
            ValidationError: If validation fails
        """
        if time_spent is None:
            return 0
        
        try:
            time_spent = int(time_spent)
        except (ValueError, TypeError):
            raise ValidationError(
                f"{field_name} must be an integer",
                field=field_name,
                value=time_spent
            )
        
        if time_spent < 0:
            raise ValidationError(
                f"{field_name} must be non-negative",
                field=field_name,
                value=time_spent
            )
        
        if time_spent > VALIDATION_RULES['MAX_TIME_SPENT']:
            raise ValidationError(
                f"{field_name} exceeds maximum allowed time",
                field=field_name,
                value=time_spent
            )
        
        return time_spent
    
    @staticmethod
    def validate_chat_log(chat_log: Any, field_name: str = "chat_log") -> List[Dict[str, Any]]:
        """
        Validate chat log structure.
        
        Args:
            chat_log: The chat log to validate
            field_name: Name of the field for error reporting
            
        Returns:
            List[Dict[str, Any]]: Validated chat log
            
        Raises:
            ValidationError: If validation fails
        """
        if chat_log is None:
            return []
        
        if isinstance(chat_log, str):
            try:
                import json
                chat_log = json.loads(chat_log)
            except json.JSONDecodeError:
                raise ValidationError(
                    f"{field_name} must be valid JSON if provided as string",
                    field=field_name,
                    value=chat_log
                )
        
        if not isinstance(chat_log, list):
            raise ValidationError(
                f"{field_name} must be a list",
                field=field_name,
                value=type(chat_log)
            )
        
        # Validate each message in the chat log
        validated_log = []
        for i, message in enumerate(chat_log):
            if not isinstance(message, dict):
                raise ValidationError(
                    f"{field_name}[{i}] must be a dictionary",
                    field=f"{field_name}[{i}]",
                    value=message
                )
            
            # Ensure required fields exist
            if 'role' not in message:
                raise ValidationError(
                    f"{field_name}[{i}] must have a 'role' field",
                    field=f"{field_name}[{i}]",
                    value=message
                )
            
            if 'content' not in message:
                raise ValidationError(
                    f"{field_name}[{i}] must have a 'content' field",
                    field=f"{field_name}[{i}]",
                    value=message
                )
            
            validated_log.append(message)
        
        return validated_log
    
    @staticmethod
    def validate_message_type_log(message_type_log: Any, field_name: str = "message_type_log") -> List[str]:
        """
        Validate message type log.
        
        Args:
            message_type_log: The message type log to validate
            field_name: Name of the field for error reporting
            
        Returns:
            List[str]: Validated message type log
            
        Raises:
            ValidationError: If validation fails
        """
        if message_type_log is None:
            return []
        
        if isinstance(message_type_log, str):
            try:
                import json
                message_type_log = json.loads(message_type_log)
            except json.JSONDecodeError:
                raise ValidationError(
                    f"{field_name} must be valid JSON if provided as string",
                    field=field_name,
                    value=message_type_log
                )
        
        if not isinstance(message_type_log, list):
            raise ValidationError(
                f"{field_name} must be a list",
                field=field_name,
                value=type(message_type_log)
            )
        
        validated_log = []
        for i, message_type in enumerate(message_type_log):
            if not isinstance(message_type, str):
                raise ValidationError(
                    f"{field_name}[{i}] must be a string",
                    field=f"{field_name}[{i}]",
                    value=message_type
                )
            validated_log.append(message_type)
        
        return validated_log
    
    @staticmethod
    def validate_class_type(class_type: Any, field_name: str = "class_type") -> str:
        """
        Validate problem class type.
        
        Args:
            class_type: The class type to validate
            field_name: Name of the field for error reporting
            
        Returns:
            str: Validated class type
            
        Raises:
            ValidationError: If validation fails
        """
        if not class_type:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=class_type
            )
        
        if not isinstance(class_type, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=class_type
            )
        
        valid_types = list(PROBLEM_TYPES.values())
        if class_type not in valid_types:
            raise ValidationError(
                f"{field_name} must be one of {valid_types}",
                field=field_name,
                value=class_type
            )
        
        return class_type
    
    @staticmethod
    def validate_scenario(scenario: Any, field_name: str = "scenario") -> Dict[str, Any]:
        """
        Validate scenario configuration.
        
        Args:
            scenario: The scenario to validate
            field_name: Name of the field for error reporting
            
        Returns:
            Dict[str, Any]: Validated scenario
            
        Raises:
            ValidationError: If validation fails
        """
        if not scenario:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=scenario
            )
        
        if not isinstance(scenario, dict):
            raise ValidationError(
                f"{field_name} must be a dictionary",
                field=field_name,
                value=type(scenario)
            )
        
        validated_scenario = {}
        
        # Validate brand
        if 'brand' in scenario:
            brand = scenario['brand']
            if brand not in list(BRAND_TYPES.values()):
                raise ValidationError(
                    f"{field_name}.brand must be one of {list(BRAND_TYPES.values())}",
                    field=f"{field_name}.brand",
                    value=brand
                )
            validated_scenario['brand'] = brand
        
        # Validate think_level
        if 'think_level' in scenario:
            think_level = scenario['think_level']
            if think_level not in list(THINK_LEVELS.values()):
                raise ValidationError(
                    f"{field_name}.think_level must be one of {list(THINK_LEVELS.values())}",
                    field=f"{field_name}.think_level",
                    value=think_level
                )
            validated_scenario['think_level'] = think_level
        
        # Validate feel_level
        if 'feel_level' in scenario:
            feel_level = scenario['feel_level']
            if feel_level not in list(FEEL_LEVELS.values()):
                raise ValidationError(
                    f"{field_name}.feel_level must be one of {list(FEEL_LEVELS.values())}",
                    field=f"{field_name}.feel_level",
                    value=feel_level
                )
            validated_scenario['feel_level'] = feel_level
        
        # Validate problem_type
        if 'problem_type' in scenario:
            problem_type = scenario['problem_type']
            if problem_type not in list(PROBLEM_TYPES.values()):
                raise ValidationError(
                    f"{field_name}.problem_type must be one of {list(PROBLEM_TYPES.values())}",
                    field=f"{field_name}.problem_type",
                    value=problem_type
                )
            validated_scenario['problem_type'] = problem_type
        
        return validated_scenario
    
    @staticmethod
    def validate_email(email: Any, field_name: str = "email") -> str:
        """
        Validate email address.
        
        Args:
            email: The email to validate
            field_name: Name of the field for error reporting
            
        Returns:
            str: Validated email
            
        Raises:
            ValidationError: If validation fails
        """
        if not email:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=email
            )
        
        if not isinstance(email, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=email
            )
        
        # Basic email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(
                f"{field_name} must be a valid email address",
                field=field_name,
                value=email
            )
        
        return email.lower().strip()
    
    @staticmethod
    def validate_confidence(confidence: Any, field_name: str = "confidence") -> float:
        """
        Validate confidence score.
        
        Args:
            confidence: The confidence to validate
            field_name: Name of the field for error reporting
            
        Returns:
            float: Validated confidence
            
        Raises:
            ValidationError: If validation fails
        """
        if confidence is None:
            return 0.0
        
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            raise ValidationError(
                f"{field_name} must be a number",
                field=field_name,
                value=confidence
            )
        
        if confidence < VALIDATION_RULES['MIN_CONFIDENCE'] or confidence > VALIDATION_RULES['MAX_CONFIDENCE']:
            raise ValidationError(
                f"{field_name} must be between {VALIDATION_RULES['MIN_CONFIDENCE']} and {VALIDATION_RULES['MAX_CONFIDENCE']}",
                field=field_name,
                value=confidence
            )
        
        return confidence
    
    @staticmethod
    def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete request data for chat endpoints.
        
        Args:
            data: The request data to validate
            
        Returns:
            Dict[str, Any]: Validated request data
            
        Raises:
            ValidationError: If validation fails
        """
        validated_data = {}
        
        # Validate required fields
        if 'message' not in data:
            raise ValidationError("message is required")
        validated_data['message'] = InputValidator.validate_message(data['message'])
        
        if 'index' not in data:
            raise ValidationError("index is required")
        validated_data['index'] = InputValidator.validate_conversation_index(data['index'])
        
        # Validate optional fields
        if 'timer' in data:
            validated_data['timer'] = InputValidator.validate_time_spent(data['timer'])
        
        if 'chatLog' in data:
            validated_data['chatLog'] = InputValidator.validate_chat_log(data['chatLog'])
        
        if 'messageTypeLog' in data:
            validated_data['messageTypeLog'] = InputValidator.validate_message_type_log(data['messageTypeLog'])
        
        if 'classType' in data:
            validated_data['classType'] = InputValidator.validate_class_type(data['classType'])
        
        if 'scenario' in data:
            validated_data['scenario'] = InputValidator.validate_scenario(data['scenario'])
        
        return validated_data


def validate_api_request(request_data: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
    """
    Validate API request data with specified required fields.
    
    Args:
        request_data: The request data to validate
        required_fields: List of required field names
        
    Returns:
        Dict[str, Any]: Validated request data
        
    Raises:
        ValidationError: If validation fails
    """
    if required_fields is None:
        required_fields = ['message', 'index']
    
    # Check for required fields
    for field in required_fields:
        if field not in request_data:
            raise ValidationError(f"{field} is required")
    
    return InputValidator.validate_request_data(request_data) 