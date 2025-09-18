from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from transformers import pipeline
from django.utils.safestring import mark_safe
from .models import Conversation
import random
import json
import openai
import os
import gc
import threading
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global ML classifier cache with thread safety
_ml_classifier = None
_classifier_lock = threading.Lock()

def get_ml_classifier():
    """Get or create ML classifier with thread-safe caching"""
    global _ml_classifier
    if _ml_classifier is None:
        with _classifier_lock:
            if _ml_classifier is None:
                try:
                    # Set environment variables for optimization
                    os.environ["TRANSFORMERS_CACHE"] = "./cache"
                    os.environ["USE_TF"] = "0"  # Disable TensorFlow
                    os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Avoid tokenizer warnings
                    
                    _ml_classifier = pipeline(
                        "text-classification", 
                        model="jpsteinhafel/complaints_classifier",
                        device=-1,  # Use CPU for better concurrency
                        batch_size=1  # Process one at a time for memory efficiency
                    )
                    logger.info("ML classifier loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load ML classifier: {e}")
                    raise e
    return _ml_classifier

def cleanup_resources():
    """Clean up resources to prevent memory leaks"""
    gc.collect()

def safe_debug_print(message):
    """Safely print debug messages without causing BrokenPipeError"""
    try:
        print(message)
        logger.info(message)
    except (BrokenPipeError, OSError):
        pass

def get_primary_problem_type(scores):
    """Get primary problem type from scores"""
    if not scores:
        return "Other", 0.0
    
    max_score = 0.0
    primary_type = "Other"
    
    for problem_type, score in scores.items():
        if score > max_score:
            max_score = score
            primary_type = problem_type
    
    return primary_type, max_score

def create_safe_link(url, text):
    """Create a safe HTML link"""
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'

class OptimizedChatAPIView(APIView):
    """Optimized ChatAPIView for high concurrency"""

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            user_input = data.get('message', '')
            conversation_index = data.get('index', 0)
            time_spent = data.get('timer', 0)
            chat_log = data.get('chatLog', '')
            class_type = data.get('classType', '')
            message_type_log = data.get('messageTypeLog', '')

            # Debug logging for session data
            safe_debug_print(f"DEBUG: POST request - Session ID: {request.session.session_key}")
            safe_debug_print(f"DEBUG: POST request - Session keys: {list(request.session.keys())}")
            safe_debug_print(f"DEBUG: POST request - Session modified: {request.session.modified}")
            
            # Get the scenario information from request data first, then fall back to session
            scenario = data.get('scenario')
            if scenario:
                safe_debug_print(f"DEBUG: Retrieved scenario from request data: {scenario}")
                # Store it in session for future requests
                request.session['scenario'] = scenario
                request.session.save()
            else:
                # Fall back to session if no scenario in request
                scenario = request.session.get('scenario')
                if scenario:
                    safe_debug_print(f"DEBUG: Retrieved scenario from session: {scenario}")
                else:
                    safe_debug_print(f"DEBUG: No scenario in session or request data, using fallback")
                    scenario = {
                        'brand': 'Basic',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }

            # Initialize response variables
            chat_response = ""
            message_type = ""
            call_closing_message = False
            is_html_message = False

            if conversation_index in (0, 1, 2, 3, 4):
                if conversation_index == 0:
                    # Check if the user is asking about returns specifically
                    return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
                    is_return_request = any(keyword in user_input.lower() for keyword in return_keywords)
                    
                    if is_return_request:
                        # Route return requests to "Return" classification - skip ML entirely
                        safe_debug_print(f"DEBUG: Return request detected, skipping ML classification")
                        class_type = "Return"
                        scores = {"A": 0.0, "B": 0.0, "C": 0.0, "Other": 0.0, "Return": 1.0}
                        safe_debug_print(f"DEBUG: Manual scores for return request: {scores}")
                    else:
                        # Use cached ML classifier for non-return requests
                        try:
                            classifier = get_ml_classifier()
                            class_response = classifier(user_input)[0]
                            all_scores = classifier(user_input, return_all_scores=True)[0]
                            scores = {}
                            for item in all_scores:
                                scores[item["label"]] = item["score"]
                            
                            # Add Return category with 0.0 weight for ML classified items
                            scores["Return"] = 0.0
                            
                            # Use multi-label detection to get primary type and all detected types
                            class_type, confidence = get_primary_problem_type(scores)
                            
                            # If the model predicts not-Other with very low confidence, treat as Other
                            if class_type != "Other" and confidence < 0.1:
                                class_type = "Other"
                            safe_debug_print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {class_response['score']}")
                            safe_debug_print(f"DEBUG: Product type breakdown scores: {scores}")
                        except Exception as e:
                            safe_debug_print(f"ERROR: ML classifier failed: {e}")
                            class_type = "Other"
                            scores = {"A": 0.0, "B": 0.0, "C": 0.0, "Other": 1.0, "Return": 0.0}
                    
                    # Store the scores in session and cache for later use (for both return and ML cases)
                    request.session['product_type_breakdown'] = scores
                    request.session.save()
                    
                    # Store the product_type_breakdown data in a temporary database record
                    temp_conversation = Conversation(
                        email="temp@temp.com",  # Temporary email
                        time_spent=0,
                        chat_log=[],
                        message_type_log=[],
                        product_type_breakdown=scores,
                        test_type=scenario['brand'],
                        problem_type=class_type,
                        think_level=scenario['think_level'],
                        feel_level=scenario['feel_level'],
                    )
                    temp_conversation.save()
                    safe_debug_print(f"DEBUG: Stored product_type_breakdown in database with ID {temp_conversation.id}: {scores}")
                    
                    # Update the scenario with the actual problem type from classifier and product_type_breakdown
                    scenario['problem_type'] = class_type
                    scenario['product_type_breakdown'] = scores
                    request.session['scenario'] = scenario
                    
                    chat_response = self.question_initial_response(class_type, user_input, scenario)
                    message_type = scenario['think_level']
                    if chat_response.startswith("Paraphrased: "):
                        message_type = "Low"
                        chat_response = chat_response[len("Paraphrased: "):]
                    message_type += class_type
                elif conversation_index in (1, 2, 3, 4):
                    # For continuation responses, use the class_type that was already determined
                    if scenario['think_level'] == "Low":
                        chat_response = self.low_question_continuation_response(chat_log, scenario)
                        message_type = " "
                    else:  # High think level
                        chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                        message_type = " "

            elif conversation_index == 5:
                # 6th message - prompt for email and end conversation
                chat_response, message_type = self.understanding_statement_response(scenario)
                # Tell frontend to call closing message API after this response
                call_closing_message = True
            elif conversation_index == 6:
                # Save conversation after user provides email
                safe_debug_print(f"DEBUG: Saving conversation at index 6")
                safe_debug_print(f"DEBUG: Saving conversation with scenario: {scenario}")
                chat_response = self.save_conversation(request, user_input, time_spent, chat_log, message_type_log, scenario)
                message_type = " "
                call_closing_message = False
                # This message contains HTML (survey link), so mark it for HTML rendering
                is_html_message = True
            else:
                # Conversation is complete, don't continue
                chat_response = " "
                message_type = " "
                call_closing_message = False

            conversation_index += 1
            
            # Prepare response data
            response_data = {
                "reply": chat_response,
                "index": conversation_index,
                "classType": class_type,
                "messageType": message_type,
                "scenario": scenario
            }
            
            # Add optional fields based on conversation state
            if call_closing_message:
                response_data['callClosingMessage'] = True
            if is_html_message:
                response_data['isHtml'] = True
            
            # Clean up resources periodically
            if conversation_index % 10 == 0:
                cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            safe_debug_print(f"ERROR in ChatAPIView: {e}")
            return Response(
                {"error": "Internal server error", "reply": "I apologize, but I'm experiencing technical difficulties. Please try again."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def question_initial_response(self, class_type, user_input, scenario=None):
        """Generate initial response based on problem type"""
        try:
            # Use the consolidated OpenAI function
            return self.get_openai_response(user_input, class_type, "initial", scenario)
        except Exception as e:
            safe_debug_print(f"ERROR in question_initial_response: {e}")
            return "I understand you're having an issue. Can you tell me more about what happened?"

    def low_question_continuation_response(self, chat_log, scenario=None):
        """Generate low-level continuation response"""
        try:
            return self.get_openai_response("", "Other", "continuation", scenario)
        except Exception as e:
            safe_debug_print(f"ERROR in low_question_continuation_response: {e}")
            return "I see. Can you provide more details about your situation?"

    def high_question_continuation_response(self, class_type, chat_log, scenario=None):
        """Generate high-level continuation response"""
        try:
            return self.get_openai_response("", class_type, "continuation", scenario)
        except Exception as e:
            safe_debug_print(f"ERROR in high_question_continuation_response: {e}")
            return "Thank you for that information. What else can you tell me about this issue?"

    def understanding_statement_response(self, scenario=None):
        """Generate understanding statement response"""
        try:
            return self.get_openai_response("", "Other", "understanding", scenario), "Low"
        except Exception as e:
            safe_debug_print(f"ERROR in understanding_statement_response: {e}")
            return "Thank you for sharing your experience with me! I will send you a set of comprehensive suggestions on how to proceed via email. Please provide your email below...", "Low"

    def get_openai_response(self, user_input, problem_type, response_type, scenario=None):
        """Consolidated OpenAI response generation with caching"""
        try:
            # Map Return to Other for response generation
            response_problem_type = "Other" if problem_type == "Return" else problem_type
            
            # Create cache key for response
            cache_key = f"openai_response_{response_problem_type}_{response_type}_{hash(user_input)}"
            cached_response = cache.get(cache_key)
            
            if cached_response:
                return cached_response
            
            # Get brand and levels from scenario
            brand = scenario.get('brand', 'Basic') if scenario else 'Basic'
            think_level = scenario.get('think_level', 'High') if scenario else 'High'
            feel_level = scenario.get('feel_level', 'High') if scenario else 'High'
            
            # Create prompts based on response type
            if response_type == "initial":
                if brand == "Lulu":
                    prompt = f"""You are a Lululemon customer service representative. A customer has reported a {response_problem_type} issue. 
                    Respond with empathy and mindfulness, keeping it to 2-3 sentences maximum. Be concise and direct.
                    Customer message: {user_input}"""
                else:
                    prompt = f"""You are a customer service representative. A customer has reported a {response_problem_type} issue. 
                    Respond professionally and helpfully, keeping it to 2-3 sentences maximum.
                    Customer message: {user_input}"""
            elif response_type == "continuation":
                if brand == "Lulu":
                    prompt = f"""You are a Lululemon customer service representative continuing a conversation about a {response_problem_type} issue. 
                    Ask a follow-up question to gather more information. Keep it to 2-3 sentences maximum. Be concise and direct."""
                else:
                    prompt = f"""You are a customer service representative continuing a conversation about a {response_problem_type} issue. 
                    Ask a follow-up question to gather more information. Keep it to 2-3 sentences maximum."""
            else:  # understanding
                if brand == "Lulu":
                    prompt = f"""You are a Lululemon customer service representative. Thank the customer for sharing their experience about a {response_problem_type} issue. 
                    Tell them you will send comprehensive suggestions via email and ask for their email address. Keep it to 2-3 sentences maximum. Be concise and direct."""
                else:
                    prompt = f"""You are a customer service representative. Thank the customer for sharing their experience about a {response_problem_type} issue. 
                    Tell them you will send comprehensive suggestions via email and ask for their email address. Keep it to 2-3 sentences maximum."""
            
            # Make OpenAI API call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Cache the response for 1 hour
            cache.set(cache_key, response_text, 3600)
            
            return response_text
            
        except Exception as e:
            safe_debug_print(f"ERROR in get_openai_response: {e}")
            return "I apologize, but I'm having trouble processing your request. Please try again."

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        """Optimized conversation saving with connection pooling"""
        try:
            safe_debug_print(f"DEBUG: Save conversation - email: {email}, time_spent: {time_spent}")
            
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            if not re.match(email_pattern, email):
                return "Please enter a valid email address in the format: example@domain.com"
            
            # Use problem_type directly from scenario
            problem_type = scenario.get('problem_type', 'Other')
            
            # Get product type breakdown from database first, then scenario, then session
            temp_conversation = None
            product_type_breakdown = None
            
            try:
                # Look for the most recent temporary conversation with product_type_breakdown data
                temp_conversations = Conversation.objects.filter(
                    email="temp@temp.com",
                    test_type=scenario['brand'],
                    problem_type=problem_type,
                    think_level=scenario['think_level'],
                    feel_level=scenario['feel_level']
                ).order_by('-created_at')
                
                if temp_conversations.exists():
                    temp_conversation = temp_conversations.first()
                    product_type_breakdown = temp_conversation.product_type_breakdown
                    safe_debug_print(f"DEBUG: Found temp conversation {temp_conversation.id} with product_type_breakdown: {product_type_breakdown}")
                else:
                    # Fallback to session data
                    product_type_breakdown = request.session.get('product_type_breakdown', None)
                    safe_debug_print(f"DEBUG: No temp conversation found, using session data: {product_type_breakdown}")
            except Exception as e:
                safe_debug_print(f"DEBUG: Error finding temp conversation: {e}")
                # Fallback to session data
                product_type_breakdown = request.session.get('product_type_breakdown', None)
                safe_debug_print(f"DEBUG: Fallback to session data: {product_type_breakdown}")

            safe_debug_print(f"DEBUG: Final product_type_breakdown: {product_type_breakdown}")
            
            # Clean up temporary conversation after saving
            if temp_conversation:
                temp_conversation.delete()
                safe_debug_print(f"DEBUG: Cleaned up temp conversation {temp_conversation.id}")
            
            # Save conversation with optimized database operations
            conversation = Conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                product_type_breakdown=product_type_breakdown,
                test_type=scenario['brand'],
                problem_type=scenario['problem_type'],
                think_level=scenario['think_level'],
                feel_level=scenario['feel_level'],
            )
            conversation.save()
            safe_debug_print(f"DEBUG: Conversation saved to database with ID: {conversation.id}")
            
            # Create safe HTML link with proper escaping
            survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
            survey_link = create_safe_link(survey_url, "Survey Link")
            
            html_message = mark_safe(
                f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
            )
            
            return html_message
            
        except Exception as e:
            safe_debug_print(f"ERROR: Failed to save conversation: {e}")
            raise e

# Keep the original classes for backward compatibility
ChatAPIView = OptimizedChatAPIView
