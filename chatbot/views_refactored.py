"""
Refactored views for the Combot Backend application.
Uses service layer and proper error handling for production-ready code.
"""

import logging
import random
from typing import Dict, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.utils.safestring import mark_safe
from django.utils.html import escape
from urllib.parse import quote

from .constants import (
    CONVERSATION_INDICES, DEFAULT_VALUES, ERROR_MESSAGES, SUCCESS_MESSAGES,
    HTTP_STATUS, RESPONSE_TYPES, PROBLEM_TYPES, MEMORY_THRESHOLDS
)
from .exceptions import (
    ValidationError, MemoryError, MLClassificationError, OpenAIError,
    DatabaseError, CacheError, ServiceUnavailableError, handle_exception
)
from .validators import InputValidator, validate_api_request
from .services import (
    conversation_service, ml_service, openai_service, 
    memory_service, cache_service
)

logger = logging.getLogger(__name__)


class BaseAPIView(APIView):
    """Base API view with common functionality."""
    
    def handle_exception(self, exc):
        """Override to use custom exception handling."""
        return handle_exception(exc, logger)
    
    def validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request data using the validator service."""
        try:
            return validate_api_request(data)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            raise
    
    def check_memory_status(self):
        """Check memory status and perform cleanup if needed."""
        try:
            if memory_service.should_trigger_cleanup():
                logger.warning("Memory threshold triggered cleanup")
                memory_service.perform_cleanup()
            
            if memory_service.increment_user_count():
                logger.info("Process recycling triggered")
                
        except MemoryError as e:
            logger.error(f"Memory management error: {e.message}")
            raise
    
    def get_scenario_from_session(self, request) -> Dict[str, Any]:
        """Get scenario from session or create default."""
        scenario = request.session.get('scenario')
        if not scenario:
            scenario = {
                'brand': DEFAULT_VALUES['TEST_TYPE'],
                'problem_type': DEFAULT_VALUES['PROBLEM_TYPE'],
                'think_level': DEFAULT_VALUES['THINK_LEVEL'],
                'feel_level': DEFAULT_VALUES['FEEL_LEVEL']
            }
            request.session['scenario'] = scenario
            request.session.save()
        
        return scenario


class ChatAPIView(BaseAPIView):
    """API view for chat functionality."""
    
    def post(self, request, *args, **kwargs):
        """Handle chat POST requests."""
        try:
            # Check memory status
            self.check_memory_status()
            
            # Validate request data
            validated_data = self.validate_request_data(request.data)
            
            # Extract validated data
            user_input = validated_data['message']
            conversation_index = validated_data['index']
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            class_type = validated_data.get('classType', '')
            message_type_log = validated_data.get('messageTypeLog', [])
            
            # Get scenario
            scenario = self.get_scenario_from_session(request)
            
            # Handle ML classification for initial messages
            if conversation_index in [CONVERSATION_INDICES['INITIAL'], CONVERSATION_INDICES['FIRST_RESPONSE']]:
                class_type = self._perform_ml_classification(user_input, scenario)
            
            # Generate response based on conversation index
            response = self._generate_response(
                conversation_index, user_input, chat_log, class_type, scenario
            )
            
            # Save conversation at save point
            if conversation_index == CONVERSATION_INDICES['SAVE_POINT']:
                self._save_conversation(
                    request, validated_data, scenario, class_type
                )
            
            return Response({
                'reply': response,
                'conversation_index': conversation_index,
                'class_type': class_type,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _perform_ml_classification(self, user_input: str, scenario: Dict[str, Any]) -> str:
        """Perform ML classification on user input."""
        try:
            result, was_cached = ml_service.classify_text(user_input)
            
            if result:
                class_type = result['primary_type']
                confidence = result['confidence']
                
                # Handle return requests with special logic
                if self._is_return_request(user_input):
                    if class_type != PROBLEM_TYPES['OTHER'] and confidence > 0.3:
                        logger.info(f"Return request but ML confident for {class_type}")
                    else:
                        class_type = PROBLEM_TYPES['OTHER']
                        logger.info("Return request with low confidence, defaulting to Other")
                
                logger.info(f"ML classification: {class_type}, confidence: {confidence}")
                return class_type
            else:
                logger.warning("ML classification returned no result")
                return PROBLEM_TYPES['OTHER']
                
        except MLClassificationError as e:
            logger.error(f"ML classification failed: {e.message}")
            return PROBLEM_TYPES['OTHER']
    
    def _is_return_request(self, user_input: str) -> bool:
        """Check if user input is a return request."""
        return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
        return any(keyword in user_input.lower() for keyword in return_keywords)
    
    def _generate_response(self, conversation_index: int, user_input: str,
                         chat_log: list, class_type: str, scenario: Dict[str, Any]) -> str:
        """Generate appropriate response based on conversation index."""
        try:
            if conversation_index == CONVERSATION_INDICES['INITIAL']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['INITIAL'],
                    user_input=user_input
                )
            
            elif conversation_index == CONVERSATION_INDICES['FIRST_RESPONSE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['SECOND_RESPONSE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['LOW_CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['PARAPHRASE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['PARAPHRASE'],
                    user_input=user_input
                )
            
            else:
                return "I understand. How can I help you further?"
                
        except OpenAIError as e:
            logger.error(f"OpenAI response generation failed: {e.message}")
            return ERROR_MESSAGES['OPENAI_ERROR']
    
    def _save_conversation(self, request, validated_data: Dict[str, Any],
                          scenario: Dict[str, Any], class_type: str):
        """Save conversation to database."""
        try:
            email = validated_data.get('email', DEFAULT_VALUES['EMAIL'])
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            message_type_log = validated_data.get('messageTypeLog', [])
            
            conversation_service.create_conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                scenario=scenario,
                product_type_breakdown=request.session.get('product_type_breakdown')
            )
            
            logger.info("Conversation saved successfully")
            
        except DatabaseError as e:
            logger.error(f"Failed to save conversation: {e.message}")
            raise


class InitialMessageAPIView(BaseAPIView):
    """API view for initial messages."""
    
    def get(self, request, *args, **kwargs):
        """Handle initial message GET requests."""
        try:
            scenario = self.get_scenario_from_session(request)
            
            # Generate initial message based on scenario
            initial_message = openai_service.generate_response(
                brand=scenario['brand'],
                think_level=scenario['think_level'],
                feel_level=scenario['feel_level'],
                problem_type=scenario.get('problem_type', PROBLEM_TYPES['A']),
                response_type=RESPONSE_TYPES['INITIAL'],
                user_input="Hello"
            )
            
            return Response({
                'message': initial_message,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)


class ClosingMessageAPIView(BaseAPIView):
    """API view for closing messages."""
    
    def get(self, request, *args, **kwargs):
        """Handle closing message GET requests."""
        try:
            scenario = self.get_scenario_from_session(request)
            
            closing_message = "Thank you for your time. Have a great day!"
            
            return Response({
                'message': closing_message,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)


class LuluAPIView(BaseAPIView):
    """API view for Lulu brand specific functionality."""
    
    def post(self, request, *args, **kwargs):
        """Handle Lulu chat POST requests."""
        try:
            # Check memory status
            self.check_memory_status()
            
            # Validate request data
            validated_data = self.validate_request_data(request.data)
            
            # Extract validated data
            user_input = validated_data['message']
            conversation_index = validated_data['index']
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            class_type = validated_data.get('classType', '')
            message_type_log = validated_data.get('messageTypeLog', [])
            
            # Get scenario with Lulu brand
            scenario = self.get_scenario_from_session(request)
            scenario['brand'] = 'Lulu'
            request.session['scenario'] = scenario
            request.session.save()
            
            # Handle ML classification for initial messages
            if conversation_index in [CONVERSATION_INDICES['INITIAL'], CONVERSATION_INDICES['FIRST_RESPONSE']]:
                class_type = self._perform_ml_classification(user_input, scenario)
            
            # Generate Lulu-specific response
            response = self._generate_lulu_response(
                conversation_index, user_input, chat_log, class_type, scenario
            )
            
            # Save conversation at save point
            if conversation_index == CONVERSATION_INDICES['SAVE_POINT']:
                self._save_conversation(
                    request, validated_data, scenario, class_type
                )
            
            return Response({
                'reply': response,
                'conversation_index': conversation_index,
                'class_type': class_type,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _perform_ml_classification(self, user_input: str, scenario: Dict[str, Any]) -> str:
        """Perform ML classification for Lulu brand."""
        try:
            result, was_cached = ml_service.classify_text(user_input)
            
            if result:
                class_type = result['primary_type']
                confidence = result['confidence']
                
                # Handle return requests with special logic
                if self._is_return_request(user_input):
                    if class_type != PROBLEM_TYPES['OTHER'] and confidence > 0.3:
                        logger.info(f"Lulu return request but ML confident for {class_type}")
                    else:
                        class_type = PROBLEM_TYPES['OTHER']
                        logger.info("Lulu return request with low confidence, defaulting to Other")
                
                logger.info(f"Lulu ML classification: {class_type}, confidence: {confidence}")
                return class_type
            else:
                logger.warning("Lulu ML classification returned no result")
                return PROBLEM_TYPES['OTHER']
                
        except MLClassificationError as e:
            logger.error(f"Lulu ML classification failed: {e.message}")
            return PROBLEM_TYPES['OTHER']
    
    def _is_return_request(self, user_input: str) -> bool:
        """Check if user input is a return request."""
        return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
        return any(keyword in user_input.lower() for keyword in return_keywords)
    
    def _generate_lulu_response(self, conversation_index: int, user_input: str,
                              chat_log: list, class_type: str, scenario: Dict[str, Any]) -> str:
        """Generate Lulu-specific response."""
        try:
            if conversation_index == CONVERSATION_INDICES['INITIAL']:
                return openai_service.generate_response(
                    brand='Lulu',
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['INITIAL'],
                    user_input=user_input
                )
            
            elif conversation_index == CONVERSATION_INDICES['FIRST_RESPONSE']:
                return openai_service.generate_response(
                    brand='Lulu',
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['SECOND_RESPONSE']:
                return openai_service.generate_response(
                    brand='Lulu',
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['LOW_CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['PARAPHRASE']:
                return openai_service.generate_response(
                    brand='Lulu',
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['PARAPHRASE'],
                    user_input=user_input
                )
            
            else:
                return "Thank you for reaching out to Lululemon. How can I assist you today?"
                
        except OpenAIError as e:
            logger.error(f"Lulu OpenAI response generation failed: {e.message}")
            return ERROR_MESSAGES['OPENAI_ERROR']
    
    def _save_conversation(self, request, validated_data: Dict[str, Any],
                          scenario: Dict[str, Any], class_type: str):
        """Save Lulu conversation to database."""
        try:
            email = validated_data.get('email', DEFAULT_VALUES['EMAIL'])
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            message_type_log = validated_data.get('messageTypeLog', [])
            
            conversation_service.create_conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                scenario=scenario,
                product_type_breakdown=request.session.get('product_type_breakdown')
            )
            
            logger.info("Lulu conversation saved successfully")
            
        except DatabaseError as e:
            logger.error(f"Failed to save Lulu conversation: {e.message}")
            raise


class LuluInitialMessageAPIView(BaseAPIView):
    """API view for Lulu initial messages."""
    
    def get(self, request, *args, **kwargs):
        """Handle Lulu initial message GET requests."""
        try:
            scenario = self.get_scenario_from_session(request)
            scenario['brand'] = 'Lulu'
            request.session['scenario'] = scenario
            request.session.save()
            
            # Generate Lulu-specific initial message
            initial_message = openai_service.generate_response(
                brand='Lulu',
                think_level=scenario['think_level'],
                feel_level=scenario['feel_level'],
                problem_type=scenario.get('problem_type', PROBLEM_TYPES['A']),
                response_type=RESPONSE_TYPES['INITIAL'],
                user_input="Hello"
            )
            
            return Response({
                'message': initial_message,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)


class LuluClosingMessageAPIView(BaseAPIView):
    """API view for Lulu closing messages."""
    
    def get(self, request, *args, **kwargs):
        """Handle Lulu closing message GET requests."""
        try:
            scenario = self.get_scenario_from_session(request)
            scenario['brand'] = 'Lulu'
            
            closing_message = "Thank you for choosing Lululemon. Have a wonderful day!"
            
            return Response({
                'message': closing_message,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)


class RandomEndpointAPIView(BaseAPIView):
    """API view for random endpoint functionality."""
    
    def get(self, request, *args, **kwargs):
        """Handle random endpoint GET requests."""
        try:
            # Check if this is a reset request
            reset = request.GET.get('reset', 'false').lower() == 'true'
            
            if reset:
                # Clear session data
                request.session.flush()
                logger.info("Session reset requested")
                return Response({
                    'message': 'Session reset successfully',
                    'status': 'reset'
                })
            
            # Generate random scenario
            scenario = {
                'brand': random.choice(['Basic', 'Lulu']),
                'problem_type': random.choice(['A', 'B', 'C', 'Other']),
                'think_level': random.choice(['High', 'Low']),
                'feel_level': random.choice(['High', 'Low'])
            }
            
            # Store scenario in session
            request.session['scenario'] = scenario
            request.session.save()
            
            logger.info(f"Random scenario generated: {scenario}")
            
            return Response({
                'scenario': scenario,
                'status': 'generated'
            })
            
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self, request, *args, **kwargs):
        """Handle random endpoint POST requests."""
        try:
            # Check memory status
            self.check_memory_status()
            
            # Validate request data
            validated_data = self.validate_request_data(request.data)
            
            # Extract validated data
            user_input = validated_data['message']
            conversation_index = validated_data['index']
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            class_type = validated_data.get('classType', '')
            message_type_log = validated_data.get('messageTypeLog', [])
            
            # Get scenario from request data or session
            scenario = validated_data.get('scenario')
            if not scenario:
                scenario = self.get_scenario_from_session(request)
            else:
                # Update session with the provided scenario
                request.session['scenario'] = scenario
                request.session.save()
            
            # Handle ML classification for initial messages
            if conversation_index in [CONVERSATION_INDICES['INITIAL'], CONVERSATION_INDICES['FIRST_RESPONSE']]:
                class_type = self._perform_ml_classification(user_input, scenario)
            
            # Generate response
            response = self._generate_response(
                conversation_index, user_input, chat_log, class_type, scenario
            )
            
            # Save conversation at save point
            if conversation_index == CONVERSATION_INDICES['SAVE_POINT']:
                self._save_conversation(
                    request, validated_data, scenario, class_type
                )
            
            return Response({
                'reply': response,
                'conversation_index': conversation_index,
                'class_type': class_type,
                'scenario': scenario
            })
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _perform_ml_classification(self, user_input: str, scenario: Dict[str, Any]) -> str:
        """Perform ML classification for random endpoint."""
        try:
            result, was_cached = ml_service.classify_text(user_input)
            
            if result:
                class_type = result['primary_type']
                confidence = result['confidence']
                
                # Handle return requests with special logic
                if self._is_return_request(user_input):
                    if class_type != PROBLEM_TYPES['OTHER'] and confidence > 0.3:
                        logger.info(f"Random endpoint return request but ML confident for {class_type}")
                    else:
                        class_type = PROBLEM_TYPES['OTHER']
                        logger.info("Random endpoint return request with low confidence, defaulting to Other")
                
                logger.info(f"Random endpoint ML classification: {class_type}, confidence: {confidence}")
                return class_type
            else:
                logger.warning("Random endpoint ML classification returned no result")
                return PROBLEM_TYPES['OTHER']
                
        except MLClassificationError as e:
            logger.error(f"Random endpoint ML classification failed: {e.message}")
            return PROBLEM_TYPES['OTHER']
    
    def _is_return_request(self, user_input: str) -> bool:
        """Check if user input is a return request."""
        return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
        return any(keyword in user_input.lower() for keyword in return_keywords)
    
    def _generate_response(self, conversation_index: int, user_input: str,
                         chat_log: list, class_type: str, scenario: Dict[str, Any]) -> str:
        """Generate response for random endpoint."""
        try:
            if conversation_index == CONVERSATION_INDICES['INITIAL']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['INITIAL'],
                    user_input=user_input
                )
            
            elif conversation_index == CONVERSATION_INDICES['FIRST_RESPONSE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['SECOND_RESPONSE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['LOW_CONTINUATION'],
                    chat_log=chat_log
                )
            
            elif conversation_index == CONVERSATION_INDICES['PARAPHRASE']:
                return openai_service.generate_response(
                    brand=scenario['brand'],
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level'],
                    problem_type=class_type,
                    response_type=RESPONSE_TYPES['PARAPHRASE'],
                    user_input=user_input
                )
            
            else:
                return "I understand. How can I help you further?"
                
        except OpenAIError as e:
            logger.error(f"Random endpoint OpenAI response generation failed: {e.message}")
            return ERROR_MESSAGES['OPENAI_ERROR']
    
    def _save_conversation(self, request, validated_data: Dict[str, Any],
                          scenario: Dict[str, Any], class_type: str):
        """Save conversation for random endpoint."""
        try:
            email = validated_data.get('email', DEFAULT_VALUES['EMAIL'])
            time_spent = validated_data.get('timer', 0)
            chat_log = validated_data.get('chatLog', [])
            message_type_log = validated_data.get('messageTypeLog', [])
            
            conversation_service.create_conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                scenario=scenario,
                product_type_breakdown=request.session.get('product_type_breakdown')
            )
            
            logger.info("Random endpoint conversation saved successfully")
            
        except DatabaseError as e:
            logger.error(f"Failed to save random endpoint conversation: {e.message}")
            raise


@api_view(['GET'])
def memory_status(request):
    """API endpoint to check memory status."""
    try:
        memory_usage = memory_service.check_memory_usage()
        
        return Response({
            'memory_usage': memory_usage,
            'memory_threshold': MEMORY_THRESHOLDS['CLEANUP'],
            'user_count': memory_service.user_count,
            'status': 'healthy' if memory_usage < MEMORY_THRESHOLDS['CLEANUP'] else 'warning'
        })
        
    except Exception as e:
        return handle_exception(e, logger) 