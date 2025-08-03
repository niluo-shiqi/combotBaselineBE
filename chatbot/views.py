from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from transformers import pipeline
from django.utils.safestring import mark_safe
from django.utils.html import escape
from urllib.parse import quote
from .models import Conversation
from transformers import pipeline
import random
import json
import openai
import os
import gc
import threading
import time
from functools import lru_cache

# Global cache for ML model to prevent reloading on every request
_ml_classifier = None
_ml_classifier_lock = threading.Lock()

# Temporary storage for product_type_breakdown data (conversation_key -> data)
_product_type_breakdown_cache = {}
_product_type_breakdown_lock = threading.Lock()

def get_ml_classifier():
    """Get or create the ML classifier with thread safety"""
    global _ml_classifier
    if _ml_classifier is None:
        with _ml_classifier_lock:
            if _ml_classifier is None:
                safe_debug_print("Loading ML classifier...")
                _ml_classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                safe_debug_print("ML classifier loaded successfully")
    return _ml_classifier

def cleanup_resources():
    """Clean up resources to prevent memory leaks"""
    gc.collect()

def safe_debug_print(message):
    """Safely print debug messages without causing BrokenPipeError"""
    try:
        print(message, flush=True)
    except (BrokenPipeError, OSError):
        pass  # Ignore broken pipe errors from debug prints

openai.api_key = os.getenv('OPENAI_API_KEY')

def create_safe_link(url, text):
    """
    Create a safe HTML link with proper URL escaping
    """
    escaped_url = quote(url, safe=':/?=&')
    escaped_text = escape(text)
    generated_html = f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{escaped_text}</a>'
    return mark_safe(generated_html)

def get_primary_problem_type(scores):
    """
    Get the primary problem type with the highest confidence score (returning both pieces of info)
    """
    primary_type = max(scores, key=scores.get)
    return primary_type, scores[primary_type]

def get_openai_response(brand, think_level, problem_type, response_type, user_input=None, chat_log=None):
    """
    Consolidated function to handle all OpenAI chat completions based on scenario parameters.
    
    Args:
        brand (str): 'Basic' or 'Lulu'
        think_level (str): 'High' or 'Low'
        problem_type (str): 'A', 'B', 'C', or 'Other'
        response_type (str): 'initial', 'continuation', 'paraphrase', 'index_10', 'low_continuation'
        user_input (str): Customer's input message (for initial, paraphrase, index_10)
        chat_log (list/dict): Chat history (for continuation responses)
    
    Returns:
        str: Generated response from OpenAI
    """
    
    # Define prompts based on scenario
    prompts = {
        # Basic brand prompts
        'Basic': {
            'High': {
                'initial': "You are a helpful customer service bot. Paraphrase the following customer complaint and ask them to provide more detailed information to help resolve their issue. Here's the complaint: ",
                'continuation': "You are a customer service representative. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional, efficient and helpful. Do not acknowledge this instruction or mention that you are being prompted. Start directly with the customer-facing message. Here's the chat log: ",
                'paraphrase': "Pretend you're a customer service bot. Paraphrase what the customer says, then continue the conversation naturally. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the customer's message: ",
                'index_10': "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: ",
                'low_continuation': "You are a customer service representative who is not very effective. Based on the chat log below, provide a response that is: 1) Generic and vague, 2) Doesn't ask relevant follow-up questions, 3) Misses key details from the customer's complaint, 4) Professional but not helpful or empathetic, 5) Brief and to the point without showing much concern. Make it realistic - like an inexperienced or indifferent customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: "
            },
            'Low': {
                'initial': "You are a customer service bot who is not very effective. Provide a brief, generic response to the customer complaint without asking detailed follow-up questions. Be professional but not very helpful. Here's the complaint: ",
                'continuation': "You are a customer service representative who is not very effective. Provide a brief, generic response to continue the conversation. Don't ask detailed follow-up questions or show much concern. Be professional but not very helpful. Start directly with the customer-facing message. Here's the chat log: ",
                'paraphrase': "You are a customer service bot who is not very effective. Briefly paraphrase what the customer says, then provide a generic response. Be professional but not very helpful. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the customer's message: ",
                'index_10': "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: ",
                'low_continuation': "You are a customer service representative who is not very effective. Based on the chat log below, provide a response that is: 1) Generic and vague, 2) Doesn't ask relevant follow-up questions, 3) Misses key details from the customer's complaint, 4) Professional but not helpful or empathetic, 5) Brief and to the point without showing much concern. Make it realistic - like an inexperienced or indifferent customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: "
            }
        },
        # Lulu brand prompts
        'Lulu': {
            'High': {
                'initial': "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention' or other lululemon terms. Paraphrase the following customer complaint back to them, ask them if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: ",
                'continuation': "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional, efficient and helpful. Start directly with the customer-facing message. Here's the chat log: ",
                'paraphrase': "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Paraphrase what the customer says, then continue the conversation naturally. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the customer's message: ",
                'index_10': "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Paraphrase the following customer complaint, ask if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: ",
                'low_continuation': "You are a Lululemon customer service representative who is well-intentioned but not very effective. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a response that is: 1) Slightly generic or vague, 2) Doesn't ask the most relevant follow-up questions, 3) May miss key details from the customer's complaint, 4) Still professional and polite but not very helpful. Make it realistic - like a well-meaning but inexperienced customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: "
            },
            'Low': {
                'initial': "You are a Lululemon customer service representative who is not very effective. Provide a brief, generic response to the customer complaint without asking detailed follow-up questions. Be professional but not very helpful. Here's the complaint: ",
                'continuation': "You are a Lululemon customer service representative who is not very effective. Provide a brief, generic response to continue the conversation. Don't ask detailed follow-up questions or show much concern. Be professional but not very helpful. Start directly with the customer-facing message. Here's the chat log: ",
                'paraphrase': "You are a Lululemon customer service representative who is not very effective. Briefly paraphrase what the customer says, then provide a generic response. Use Lululemon terms like 'gear' but be brief and not very helpful. Be professional but not very helpful. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the customer's message: ",
                'index_10': "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Paraphrase the following customer complaint, ask if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: ",
                'low_continuation': "You are a Lululemon customer service representative who is well-intentioned but not very effective. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a response that is: 1) Slightly generic or vague, 2) Doesn't ask the most relevant follow-up questions, 3) May miss key details from the customer's complaint, 4) Still professional and polite but not very helpful. Make it realistic - like a well-meaning but inexperienced customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: "
            }
        }
    }
    
    try:
        # Get the appropriate prompt
        prompt = prompts[brand][think_level][response_type]
        
        # Prepare the content based on response type
        if response_type in ['initial', 'paraphrase', 'index_10']:
            content = prompt + user_input
        else:  # continuation or low_continuation
            chat_logs_string = json.dumps(chat_log, indent=2)
            content = prompt + chat_logs_string
        
        # Make the OpenAI call
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": content}],
        )
        
        response = completion["choices"][0]["message"]["content"].strip('"')
        
        # Add "Paraphrased: " prefix for paraphrase responses
        if response_type == 'paraphrase':
            response = "Paraphrased: " + response
            
        return response
        
    except Exception as e:
        safe_debug_print(f"An error occurred in get_openai_response: {e}")
        # Return appropriate fallback responses
        if response_type == 'initial':
            return "I understand. Could you tell me more about your situation?"
        elif response_type == 'continuation':
            return "I understand. Could you tell me more about your situation so I can help you better?"
        elif response_type == 'low_continuation':
            return "I see. Let me check on that for you."
        elif response_type == 'paraphrase':
            return "Paraphrased: I understand your concern. Could you provide more details?"
        elif response_type == 'index_10':
            return "I understand your complaint. Could you provide more information?"

class ChatAPIView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            user_input = data.get('message', '')
            conversation_index = data.get('index', 0)
            time_spent = data.get('timer', 0)
            chat_log = data.get('chatLog', '')
            class_type = data.get('classType', '')
            message_type_log = data.get('messageTypeLog', '')
            
            # Get the scenario information from the session or request data
            scenario = request.session.get('scenario')
            if not scenario:
                # Try to get scenario from request data (frontend fallback)
                scenario = data.get('scenario')
                if scenario:
                    safe_debug_print(f"DEBUG: Retrieved scenario from request data: {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    safe_debug_print(f"DEBUG: No scenario in session or request data, using fallback")
                    scenario = {
                        'brand': 'Basic',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }
            else:
                safe_debug_print(f"DEBUG: Retrieved scenario from session: {scenario}")

            if conversation_index in (0, 1, 2, 3, 4):
                if conversation_index == 0:
                    os.environ["TRANSFORMERS_CACHE"] = "./cache"  # Optional, for local storage
                    os.environ["USE_TF"] = "0"  # Disable TensorFlow
                    
                    # Check if the user is asking about returns specifically
                    return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
                    is_return_request = any(keyword in user_input.lower() for keyword in return_keywords)
                    
                    if is_return_request:
                        # Route return requests to "Other" classification for OpenAI handling
                        main_type = "Other"
                    else:
                        # Use cached ML classifier instead of loading on every request
                        try:
                            classifier = get_ml_classifier()
                            all_scores = classifier(user_input, return_all_scores=True)[0]
                            scores = {}
                            for item in all_scores:
                                scores[item["label"]] = item["score"] #store each category(a,b,c,other) and its score
                            
                            # Store the scores in session and cache for later use
                            request.session['product_type_breakdown'] = scores
                            request.session.save()
                            
                            # Store the product_type_breakdown data in a temporary database record
                            from .models import Conversation
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
                            print(f"DEBUG: Stored product_type_breakdown in database with ID {temp_conversation.id}: {scores}")
                            safe_debug_print(f"DEBUG: Stored product_type_breakdown in database with ID {temp_conversation.id}: {scores}")
                            
                            
                            # Use multi-label detection to get primary type and all detected types
                            class_type, confidence = get_primary_problem_type(scores)
                            
                            # If the model predicts not-Other with very low confidence, treat as Other
                            if class_type != "Other" and confidence < 0.1:
                                class_type = "Other"
                            safe_debug_print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
                            safe_debug_print(f"DEBUG: Product type breakdown scores: {scores}")
                        except Exception as e:
                            safe_debug_print(f"ERROR: ML classifier failed: {e}")
                            class_type = "Other"
                            scores = {}
                    
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
                    # Get class_type from the updated scenario, not from request data
                    class_type = scenario.get('problem_type', 'Other')
                    # Use scenario's think_level to determine response type
                    if scenario['think_level'] == "Low":
                        chat_response = self.low_question_continuation_response(chat_log, scenario)
                        message_type = " "
                    else:  # High think level
                        chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                        message_type = " "

            elif conversation_index == 5:
                chat_response, message_type = self.understanding_statement_response(scenario)
                # Tell frontend to call closing message API after this response
                call_closing_message = True
            elif conversation_index == 6:
                # Save conversation after user provides email
                safe_debug_print(f"DEBUG: Saving conversation at index 7")
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
            
            # Ensure class_type is always from the scenario
            if not class_type or class_type == "":
                class_type = scenario.get('problem_type', 'Other')
            
            response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
            # Add scenario to response for frontend to send back
            response_data['scenario'] = scenario
            
            # Add callClosingMessage flag if needed
            if conversation_index == 6:  # After increment, this means the original index was 5
                response_data['callClosingMessage'] = True
            
            # Add isHtml flag if this message contains HTML (survey link)
            if conversation_index == 7:  # After increment, this means the original index was 6
                response_data['isHtml'] = True
            
            # Debug logging for scenario data
            safe_debug_print(f"DEBUG: Response - conversation_index: {conversation_index}, class_type: {class_type}")
            safe_debug_print(f"DEBUG: Response - scenario: {scenario}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            safe_debug_print(f"ERROR in ChatAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input, scenario):
        # Use predefined responses for A, B, C problem types
        if class_type in ["A", "B", "C"]:
            if scenario['brand'] == "Lulu":
                A_responses_high = [
                    "I'd love to hear more about what's going on with your gear. Can you walk me through the details?",
                    "When did you first notice this wasn't performing as expected?",
                    "Have you tried any troubleshooting steps on your own? We want to make sure you're getting the most out of your gear.",
                    "Are you following the care instructions we recommend? Sometimes that can make all the difference.",
                    "What would be your ideal resolution? We're here to make sure you're stoked about your gear.",
                ]

                B_responses_high = [
                    "What's the expected delivery date for your order? We want to make sure you get your gear when you need it.",
                    "Have you received any updates about your delivery status? We're tracking this closely.",
                    "Have you checked in with the carrier or delivery service? Sometimes they have the most up-to-date info.",
                    "Would you prefer a refund or store credit? We want to make this right for you.",
                    "Are you still excited about your order, or would you rather cancel and try again? No pressure either way.",
                ]

                C_responses_high = [
                    "I'd love to hear more about your experience with our team member. Can you share the details?",
                    "When and where did this interaction happen? We want to understand the full picture.",
                    "Can you tell me about the specific situation that left you feeling this way? We take this seriously.",
                    "How did the team member's behavior come across? We want to make sure everyone feels welcome and supported.",
                ]
            else:  # Basic
                A_responses_high = [
                    "Can you describe the problem in more detail?",
                    "When did you first notice the issue?",
                    "Have you tried to resolve the problem on your own?",
                    "Have you used the product as intended and followed any instructions provided?",
                    "Is there a specific resolution or solution you are hoping for?",
                ]

                B_responses_high = [
                    "What was the expected delivery date?",
                    "Have you received any updates or notifications regarding your delivery?",
                    "Have you tried reaching out to the carrier or delivery service?",
                    "Would you like to receive a refund or store credit for the inconvenience?",
                    "Are you still hoping to receive the order or would you like to cancel it?",
                ]

                C_responses_high = [
                    "Can you provide us with more details about the interaction with the employee?",
                    "When and where did the interaction take place?",
                    "Was there a specific instance or series of incidents that led to you feeling mistreated?",
                    "How did the employee behave in a rude or disrespectful manner?",
                ]

            # Select appropriate response list based on class_type
            response_list = {
                "A": A_responses_high,
                "B": B_responses_high,
                "C": C_responses_high
            }[class_type]

            chat_response = random.choice([
                random.choice(response_list),
                self.paraphrase_response(user_input, scenario)
            ])
        elif class_type == "Other":
            # Use the consolidated OpenAI function for "Other" classification
            chat_response = get_openai_response(
                brand=scenario['brand'],
                think_level=scenario['think_level'],
                problem_type=class_type,
                response_type='initial',
                user_input=user_input
            )

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log, scenario):
        # Use predefined responses for A, B, C problem types
        if class_type in ["A", "B", "C"]:
            if scenario['brand'] == "Lulu":
                A_responses_high = [
                "I'd love to hear more about what's going on with your gear. Can you walk me through the details?",
                "When did you first notice this wasn't performing as expected?",
                "Have you tried any troubleshooting steps on your own? We want to make sure you're getting the most out of your gear.",
                "Are you following the care instructions we recommend? Sometimes that can make all the difference.",
                "What would be your ideal resolution? We're here to make sure you're stoked about your gear.",
            ]

                B_responses_high = [
                "What's the expected delivery date for your order? We want to make sure you get your gear when you need it.",
                "Have you received any updates about your delivery status? We're tracking this closely.",
                "Have you checked in with the carrier or delivery service? Sometimes they have the most up-to-date info.",
                "Would you prefer a refund or store credit? We want to make this right for you.",
                "Are you still excited about your order, or would you rather cancel and try again? No pressure either way.",
            ]

                C_responses_high = [
                "I'd love to hear more about your experience with our team member. Can you share the details?",
                "When and where did this interaction happen? We want to understand the full picture.",
                "Can you tell me about the specific situation that left you feeling this way? We take this seriously.",
                "How did the team member's behavior come across? We want to make sure everyone feels welcome and supported.",
            ]
            else:  # Basic
                A_responses_high = [
                    "Can you describe the problem in more detail?",
                    "When did you first notice the issue?",
                    "Have you tried to resolve the problem on your own?",
                    "Have you used the product as intended and followed any instructions provided?",
                    "Is there a specific resolution or solution you are hoping for?",
                ]

                B_responses_high = [
                    "What was the expected delivery date?",
                    "Have you received any updates or notifications regarding your delivery?",
                    "Have you tried reaching out to the carrier or delivery service?",
                    "Would you like to receive a refund or store credit for the inconvenience?",
                    "Are you still hoping to receive the order or would you like to cancel it?",
                ]

                C_responses_high = [
                    "Can you provide us with more details about the interaction with the employee?",
                    "When and where did the interaction take place?",
                    "Was there a specific instance or series of incidents that led to you feeling mistreated?",
                    "How did the employee behave in a rude or disrespectful manner?",
                ]

            # Select appropriate response list based on class_type
            response_list = {
                "A": A_responses_high,
                "B": B_responses_high,
                "C": C_responses_high
            }[class_type]

            chat_response = self.select_next_response(chat_log, response_list.copy())
        elif class_type == "Other":
            # Use the consolidated OpenAI function for "Other" classification
            chat_response = get_openai_response(
                brand=scenario['brand'],
                think_level=scenario['think_level'],
                problem_type=class_type,
                response_type='continuation',
                chat_log=chat_log
            )
        return chat_response

    def low_question_continuation_response(self, chat_log, scenario=None):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a default response
                return "I see. Let me check on that for you."
        
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='low_continuation',
            chat_log=chat_log
        )


    def select_next_response(self, chat_log, response_options):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a random response
                return random.choice(response_options) if response_options else "I understand. Could you tell me more about your situation?"
        
        # Ensure chat_log is a list
        if not isinstance(chat_log, list):
            # If chat_log is not a list, return a random response
            return random.choice(response_options) if response_options else "I understand. Could you tell me more about your situation?"
        
        # Collect all messages from 'combot'
        combot_messages = []
        for message in chat_log:
            if isinstance(message, dict):
                # Handle both 'sender' and 'role' formats
                if message.get('sender') == 'combot' or message.get('role') == 'assistant':
                    text = message.get('text') or message.get('content', '')
                    if text:
                        combot_messages.append(text)

        # Exclude all messages that have already been used by 'combot'
        updated_response_options = [option for option in response_options if option not in combot_messages]

        # Randomly select the next response from the remaining options
        if updated_response_options:  # Ensure the list is not empty
            return random.choice(updated_response_options)
        else:
            return "I understand. Could you tell me more about your situation?"

    def understanding_statement_response(self, scenario):
        feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect. Please hold on while I check with my manager..."
        feel_response_low = "I see. Let me check on that for you."

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='index_10',
            user_input=user_input
        )

    def paraphrase_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='paraphrase',
            user_input=user_input
        )

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        safe_debug_print(f"DEBUG: Saving conversation with scenario: {scenario}")
        safe_debug_print(f"DEBUG: Save conversation - email: {email}, time_spent: {time_spent}")
        safe_debug_print(f"DEBUG: Save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        safe_debug_print(f"DEBUG: Save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        safe_debug_print(f"DEBUG: Save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        safe_debug_print(f"DEBUG: Save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        safe_debug_print(f"DEBUG: Save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Use problem_type directly from scenario
        problem_type = scenario.get('problem_type', 'Other')
        safe_debug_print(f"DEBUG: Save conversation - problem_type from scenario: {problem_type}")
        
        # Get product type breakdown from database first, then scenario, then session
        from .models import Conversation
        
        # Look for the most recent temporary conversation with product_type_breakdown data
        temp_conversation = None
        try:
            temp_conversation = Conversation.objects.filter(
                email="temp@temp.com",
                product_type_breakdown__isnull=False
            ).order_by('-created_at').first()
        except Exception as e:
            print(f"DEBUG: Error finding temp conversation: {e}")
            safe_debug_print(f"DEBUG: Error finding temp conversation: {e}")
        
        cached_data = temp_conversation.product_type_breakdown if temp_conversation else None
        product_type_breakdown = cached_data or scenario.get('product_type_breakdown') or request.session.get('product_type_breakdown', None)
        
        print(f"DEBUG: Save conversation - temp_conversation_id: {temp_conversation.id if temp_conversation else None}")
        print(f"DEBUG: Save conversation - product_type_breakdown from database: {cached_data}")
        print(f"DEBUG: Save conversation - product_type_breakdown from scenario: {scenario.get('product_type_breakdown', None)}")
        print(f"DEBUG: Save conversation - product_type_breakdown from session: {request.session.get('product_type_breakdown', None)}")
        print(f"DEBUG: Save conversation - final product_type_breakdown: {product_type_breakdown}")
        
        safe_debug_print(f"DEBUG: Save conversation - temp_conversation_id: {temp_conversation.id if temp_conversation else None}")
        safe_debug_print(f"DEBUG: Save conversation - product_type_breakdown from database: {cached_data}")
        safe_debug_print(f"DEBUG: Save conversation - product_type_breakdown from scenario: {scenario.get('product_type_breakdown', None)}")
        safe_debug_print(f"DEBUG: Save conversation - product_type_breakdown from session: {request.session.get('product_type_breakdown', None)}")
        safe_debug_print(f"DEBUG: Save conversation - final product_type_breakdown: {product_type_breakdown}")
        
        # Clean up temporary conversation after saving
        if temp_conversation:
            temp_conversation.delete()
            print(f"DEBUG: Cleaned up temp conversation {temp_conversation.id}")
            safe_debug_print(f"DEBUG: Cleaned up temp conversation {temp_conversation.id}")
            
        
        try:
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
            safe_debug_print(f"DEBUG: About to save conversation to database...")
            conversation.save()
            safe_debug_print(f"DEBUG: Conversation saved to database with ID: {conversation.id}")
            
            # Manually trigger the Google Sheets export
            try:
                from .signals import export_to_google_sheets
                export_to_google_sheets(Conversation, conversation, True)
                safe_debug_print(f"DEBUG: Manually triggered Google Sheets export for conversation {conversation.id}")
            except Exception as export_error:
                safe_debug_print(f"ERROR: Failed to export to Google Sheets: {export_error}")
        except Exception as e:
            safe_debug_print(f"ERROR: Failed to save conversation: {e}")
            safe_debug_print(f"ERROR: email={email}, time_spent={time_spent}, chat_log type={type(chat_log)}")
            safe_debug_print(f"ERROR: message_type_log type={type(message_type_log)}, scenario={scenario}")
            raise e

        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"THANK YOU for sharing your experience with me! I will send you a set of comprehensive "
            f"suggestions via email. "
            f"Please provide your email address below...<br><br>"
            f"{survey_link}"
        )
        
        return html_message


class InitialMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Use scenario from session (set by RandomEndpointAPIView)
        scenario = request.session.get('scenario')
        if not scenario:
            # Only use fallback if session is completely lost
            scenario = {
                'brand': 'Basic',
                'problem_type': 'A',
                'think_level': 'High',
                'feel_level': 'High'
            }
            request.session['scenario'] = scenario
        
        # Get the appropriate initial message based on brand and think level
        brand = scenario['brand']
        think_level = scenario['think_level']

        if think_level == "High":
            initial_message = {
                "message": "Hi there! I'm Combot, and it's great to meet you. I'm here to help with any product or " +
                            "service problems you may have encountered in the past few months. This could include issues like " +
                            "a defective product, a delayed package, or a rude employee. My goal is to provide you with the best " +
                            "guidance to resolve your issue. Please start by recounting your bad experiences with as many " +
                            "details as possible (when, how, and what happened). " +
                            "While I specialize in handling these issues, I am not Alexa or Siri. " +
                            "Let's work together to resolve your problem!" + " Please state your problem immediately following this message!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "The purpose of Combot is to assist you with any product or service problems you have " +
                            "experienced in the past few months. Examples of issues include defective products, delayed packages, or " +
                            "rude frontline employees. Combot is designed to provide optimal guidance to resolve your issue. " +
                            "Please provide a detailed account of your negative experiences, including when, how, and what occurred. " +
                            "Note that Combot specializes in handling product or service issues and is not a general-purpose " +
                            "assistant like Alexa or Siri. Let us proceed to resolve your problem." + " Please state your problem immediately following this message."
            }

        # Include all scenario information in the response
        response_data = {
            "message": initial_message['message'],
            "scenario": {
                "brand": brand,
                "problem_type": scenario['problem_type'],
                "think_level": think_level,
                "feel_level": scenario['feel_level']
            }
        }

        safe_debug_print(f"DEBUG: InitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        safe_debug_print(f"DEBUG: InitialMessageAPIView - Response data: {response_data}")

        return Response(response_data)


class ClosingMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        html_message = mark_safe(
            "THANK YOU for sharing your experience with me! I will send you a set of comprehensive "
            "suggestions via email. "
            "Please provide your email below..."
        )
        return Response({"message": html_message})


class LuluInitialMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Use scenario from session (set by RandomEndpointAPIView)
        scenario = request.session.get('scenario')
        if not scenario:
            # Only use fallback if session is completely lost
            scenario = {
                'brand': 'Lulu',
                'problem_type': 'A',
                'think_level': 'High',
                'feel_level': 'High'
            }
            request.session['scenario'] = scenario
        
        think_level = scenario['think_level']
        
        if think_level == "High":
            initial_message = {
                "message": "Hey there! I'm your Lululemon Combot, and I'm stoked to connect with you today. I'm here to help with any gear or service experiences you've had in the past few months. My intention is to make sure you feel supported and heard throughout our conversation. Let's work together to get you back to feeling amazing!" + " Please state your problem immediately following this message!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "Hi, I'm Lululemon's Combot. I can help with gear issues. Please describe your problem." + " Please state your problem immediately following this message."
            }

        # Include all scenario information in the response
        response_data = {
            "message": initial_message['message'],
            "scenario": {
                "brand": scenario['brand'],
                "problem_type": scenario['problem_type'],
                "think_level": scenario['think_level'],
                "feel_level": scenario['feel_level']
            }
        }
        
        safe_debug_print(f"DEBUG: LuluInitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        safe_debug_print(f"DEBUG: LuluInitialMessageAPIView - Response data: {response_data}")
        
        return Response(response_data)


class LuluClosingMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        html_message = mark_safe(
            "THANK YOU for sharing your experience with me! I will send you a set of comprehensive "
            "suggestions via email. "
            "Please provide your email address below..."
        )
        return Response({"message": html_message})


class LuluAPIView(APIView):

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
            safe_debug_print(f"DEBUG: Lulu POST request - Session ID: {request.session.session_key}")
            safe_debug_print(f"DEBUG: Lulu POST request - Session keys: {list(request.session.keys())}")
            safe_debug_print(f"DEBUG: Lulu POST request - Session modified: {request.session.modified}")
            
            # Get the scenario information from the session or request data
            scenario = request.session.get('scenario')
            if not scenario:
                # Try to get scenario from request data (frontend fallback)
                scenario = data.get('scenario')
                if scenario:
                    safe_debug_print(f"DEBUG: Retrieved scenario from request data (Lulu): {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    safe_debug_print(f"DEBUG: No scenario in session or request data (Lulu), using fallback")
                    scenario = {
                        'brand': 'Lulu',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }
            else:
                safe_debug_print(f"DEBUG: Retrieved scenario from session (Lulu): {scenario}")

            if conversation_index in (0, 1, 2, 3, 4):
                if conversation_index == 0:
                    # Check if the user is asking about returns specifically
                    return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
                    is_return_request = any(keyword in user_input.lower() for keyword in return_keywords)
                    
                    if is_return_request:
                        # Route return requests to "Other" classification for OpenAI handling
                        class_type = "Other"
                    else:
                        # Use cached ML classifier instead of loading on every request
                        try:
                            classifier = get_ml_classifier()
                            class_response = classifier(user_input)[0]
                            all_scores = classifier(user_input, return_all_scores=True)[0]
                            scores = {}
                            for item in all_scores:
                                scores[item["label"]] = item["score"] #store each category(a,b,c,other) and its score
                            
                            # Store the scores in session for later use
                            request.session['product_type_breakdown'] = scores
                            request.session.save()
                            
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
                            scores = {}
                    # Update the scenario with the actual problem type from classifier
                    scenario['problem_type'] = class_type
                    request.session['scenario'] = scenario
                    
                    chat_response = self.question_initial_response(class_type, user_input, scenario)
                    message_type = scenario['think_level']
                    if chat_response.startswith("Paraphrased: "):
                        message_type = "Low"
                        chat_response = chat_response[len("Paraphrased: "):]
                    message_type += class_type
                elif conversation_index in (1, 2, 3, 4):
                    # Get class_type from the updated scenario, not from request data
                    class_type = scenario.get('problem_type', 'Other')
                    # Use scenario's think_level to determine response type
                    if scenario['think_level'] == "Low":
                        chat_response = self.low_question_continuation_response(chat_log, scenario)
                        message_type = " "
                    else:  # High think level
                        chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                        message_type = " "

            elif conversation_index == 5:
                chat_response, message_type = self.understanding_statement_response(scenario)
                # Tell frontend to call closing message API after this response
                call_closing_message = True
            elif conversation_index == 6:
                # Save conversation after user provides email
                safe_debug_print(f"DEBUG: Saving conversation at index 6 (Lulu)")
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
            
            # Ensure class_type is always from the scenario
            if not class_type or class_type == "":
                class_type = scenario.get('problem_type', 'Other')
            
            response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
            # Add scenario to response for frontend to send back
            response_data['scenario'] = scenario
            
            # Add callClosingMessage flag if needed
            if conversation_index == 6:  # After increment, this means the original index was 5
                response_data['callClosingMessage'] = True
            
            # Add isHtml flag if this message contains HTML (survey link)
            if conversation_index == 7:  # After increment, this means the original index was 6
                response_data['isHtml'] = True
            
            # Debug logging for scenario data
            safe_debug_print(f"DEBUG: Lulu Response - conversation_index: {conversation_index}, class_type: {class_type}")
            safe_debug_print(f"DEBUG: Lulu Response - scenario: {scenario}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            safe_debug_print(f"ERROR in LuluAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input, scenario):
        # Use predefined responses for A, B, C problem types
        if class_type in ["A", "B", "C"]:
            A_responses_high = [
                "I'd love to hear more about what's going on with your gear. Can you walk me through the details?",
                "When did you first notice this wasn't performing as expected?",
                "Have you tried any troubleshooting steps on your own? We want to make sure you're getting the most out of your gear.",
                "Are you following the care instructions we recommend? Sometimes that can make all the difference.",
                "What would be your ideal resolution? We're here to make sure you're stoked about your gear.",
            ]

            B_responses_high = [
                "What's the expected delivery date for your order? We want to make sure you get your gear when you need it.",
                "Have you received any updates about your delivery status? We're tracking this closely.",
                "Have you checked in with the carrier or delivery service? Sometimes they have the most up-to-date info.",
                "Would you prefer a refund or store credit? We want to make this right for you.",
                "Are you still excited about your order, or would you rather cancel and try again? No pressure either way.",
            ]

            C_responses_high = [
                "I'd love to hear more about your experience with our team member. Can you share the details?",
                "When and where did this interaction happen? We want to understand the full picture.",
                "Can you tell me about the specific situation that left you feeling this way? We take this seriously.",
                "How did the team member's behavior come across? We want to make sure everyone feels welcome and supported.",
            ]

            # Select appropriate response list based on class_type
            response_list = {
                "A": A_responses_high,
                "B": B_responses_high,
                "C": C_responses_high
            }[class_type]

            chat_response = random.choice([
                random.choice(response_list),
                self.paraphrase_response(user_input, scenario)
            ])
        elif class_type == "Other":
            # Use the consolidated OpenAI function for "Other" classification
            chat_response = get_openai_response(
                brand=scenario['brand'],
                think_level=scenario['think_level'],
                problem_type=class_type,
                response_type='initial',
                user_input=user_input
            )

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log, scenario):
        # Use predefined responses for A, B, C problem types
        if class_type in ["A", "B", "C"]:
            A_responses_high = [
                "I'd love to hear more about what's going on with your gear. Can you walk me through the details?",
                "When did you first notice this wasn't performing as expected?",
                "Have you tried any troubleshooting steps on your own? We want to make sure you're getting the most out of your gear.",
                "Are you following the care instructions we recommend? Sometimes that can make all the difference.",
                "What would be your ideal resolution? We're here to make sure you're stoked about your gear.",
            ]

            B_responses_high = [
                "What's the expected delivery date for your order? We want to make sure you get your gear when you need it.",
                "Have you received any updates about your delivery status? We're tracking this closely.",
                "Have you checked in with the carrier or delivery service? Sometimes they have the most up-to-date info.",
                "Would you prefer a refund or store credit? We want to make this right for you.",
                "Are you still excited about your order, or would you rather cancel and try again? No pressure either way.",
            ]

            C_responses_high = [
                "I'd love to hear more about your experience with our team member. Can you share the details?",
                "When and where did this interaction happen? We want to understand the full picture.",
                "Can you tell me about the specific situation that left you feeling this way? We take this seriously.",
                "How did the team member's behavior come across? We want to make sure everyone feels welcome and supported.",
            ]

            # Select appropriate response list based on class_type
            response_list = {
                "A": A_responses_high,
                "B": B_responses_high,
                "C": C_responses_high
            }[class_type]

            chat_response = self.select_next_response(chat_log, response_list.copy())
        elif class_type == "Other":
            # Use the consolidated OpenAI function for "Other" classification
            chat_response = get_openai_response(
                brand=scenario['brand'],
                think_level=scenario['think_level'],
                problem_type=class_type,
                response_type='continuation',
                chat_log=chat_log
            )
        return chat_response

    def low_question_continuation_response(self, chat_log, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='low_continuation',
            chat_log=chat_log
        )


    def select_next_response(self, chat_log, response_options):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a random response
                return random.choice(response_options) if response_options else "I understand. Could you tell me more about your situation?"
        
        # Ensure chat_log is a list
        if not isinstance(chat_log, list):
            # If chat_log is not a list, return a random response
            return random.choice(response_options) if response_options else "I understand. Could you tell me more about your situation?"
        
        # Collect all messages from 'combot'
        combot_messages = []
        for message in chat_log:
            if isinstance(message, dict):
                # Handle both 'sender' and 'role' formats
                if message.get('sender') == 'combot' or message.get('role') == 'assistant':
                    text = message.get('text') or message.get('content', '')
                    if text:
                        combot_messages.append(text)

        # Exclude all messages that have already been used by 'combot'
        updated_response_options = [option for option in response_options if option not in combot_messages]

        # Randomly select the next response from the remaining options
        if updated_response_options:  # Ensure the list is not empty
            return random.choice(updated_response_options)
        else:
            return "I understand. Could you tell me more about your situation?"

    def understanding_statement_response(self, scenario):
        if scenario['brand'] == "Lulu":
            feel_response_high = "I totally understand how frustrating this must be for you. That's definitely not the experience we want you to have with your gear. Let me connect with my team to make sure we get this sorted out for you..."
            
        else:
            feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect. Please hold on while I check with my manager..."
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='index_10',
            user_input=user_input
        )

    def paraphrase_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='paraphrase',
            user_input=user_input
        )

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        safe_debug_print(f"DEBUG: Lulu save_conversation called with scenario: {scenario}")
        safe_debug_print(f"DEBUG: Lulu save conversation - email: {email}, time_spent: {time_spent}")
        safe_debug_print(f"DEBUG: Lulu save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        safe_debug_print(f"DEBUG: Lulu save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        safe_debug_print(f"DEBUG: Lulu save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        safe_debug_print(f"DEBUG: Lulu save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        safe_debug_print(f"DEBUG: Lulu save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Get product type breakdown from session if available
        product_type_breakdown = request.session.get('product_type_breakdown', None)
        safe_debug_print(f"DEBUG: Lulu save conversation - product_type_breakdown: {product_type_breakdown}")
        
        try:
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
            safe_debug_print(f"DEBUG: About to save Lulu conversation to database...")
            conversation.save()
            safe_debug_print(f"DEBUG: Lulu conversation saved to database with ID: {conversation.id}")
        except Exception as e:
            safe_debug_print(f"ERROR: Failed to save Lulu conversation: {e}")
            safe_debug_print(f"ERROR: email={email}, time_spent={time_spent}, chat_log type={type(chat_log)}")
            safe_debug_print(f"ERROR: message_type_log type={type(message_type_log)}, scenario={scenario}")
            raise e

        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
        )

        return html_message
        


class RandomEndpointAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Check if this is a reset request
        if request.path.endswith('/reset/'):
            # Clear the session
            request.session.flush()
            return Response({"message": "Session cleared successfully"})
        
        # Get the path to determine which endpoint this is
        path = request.path
        
        if path.endswith('/initial/'):
            # Handle initial message request - 8-way random choice
            choices = ['general_hight_lowf', 'general_lowt_lowf', 'lulu_hight_lowf', 'lulu_lowt_lowf', 'general_hight_highf', 'general_lowt_highf', 'lulu_hight_highf', 'lulu_lowt_highf']
            choice = random.choice(choices)
            request.session['endpoint_type'] = choice
            safe_debug_print(f"DEBUG: Random choice selected: {choice} from options: {choices}")
            safe_debug_print(f"DEBUG: This should be 12.5% chance for each option (8 total options)")
            
            # Initialize scenario with default values
            scenario = {
                'problem_type': "Other"
            }
            
            # Set brand based on choice
            if "general" in choice:
                scenario['brand'] = 'Basic'
            elif "lulu" in choice:
                scenario['brand'] = 'Lulu'
            else:
                scenario['brand'] = 'Basic'
            
            # Set feel level based on choice
            if "lowf" in choice:
                scenario['feel_level'] = 'Low'
            elif "highf" in choice:
                scenario['feel_level'] = 'High'
            else:
                scenario['feel_level'] = 'High'  # default
            
            # Set think level based on choice
            if "lowt" in choice:
                scenario['think_level'] = 'Low'
            elif "hight" in choice:
                scenario['think_level'] = 'High'
            else:
                scenario['think_level'] = 'High'  # default
            
            # Store scenario in session
            request.session['scenario'] = scenario
            request.session.save()  # Explicitly save the session
            safe_debug_print(f"DEBUG: Set scenario for {choice}: {scenario}")
            
            # Route to appropriate initial view
            if scenario['brand'] == 'Lulu':
                safe_debug_print(f"DEBUG: Routing to LuluInitialMessageAPIView with scenario: {scenario}")
                lulu_initial_view = LuluInitialMessageAPIView()
                response = lulu_initial_view.get(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
            else:
                safe_debug_print(f"DEBUG: Routing to InitialMessageAPIView with scenario: {scenario}")
                initial_view = InitialMessageAPIView()
                response = initial_view.get(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
        
        elif path.endswith('/closing/'):
            # Handle closing message request
            endpoint_type = request.session.get('endpoint_type', 'general_hight_highf')
            
            if 'lulu' in endpoint_type:
                # Use the Lulu closing message view
                lulu_closing_view = LuluClosingMessageAPIView()
                return lulu_closing_view.get(request, *args, **kwargs)
            else:
                # Use the general closing message view
                closing_view = ClosingMessageAPIView()
                return closing_view.get(request, *args, **kwargs)
        
        else:
            # Handle main endpoint request
            endpoint_type = random.choice(['general_hight_highf', 'general_hight_lowf', 'general_lowt_highf', 'general_lowt_lowf', 'lulu_hight_highf', 'lulu_hight_lowf', 'lulu_lowt_highf', 'lulu_lowt_lowf'])
            request.session['endpoint_type'] = endpoint_type
            safe_debug_print(f"DEBUG: Main endpoint random choice selected: {endpoint_type}")
            
            # Also set the scenario based on the endpoint_type
            scenario = {
                'problem_type': "not yet assigned"
            }
            
            # Set brand based on endpoint_type
            if "lulu" in endpoint_type:
                scenario['brand'] = 'Lulu'
            else:
                scenario['brand'] = 'Basic'
            
            # Set feel level based on endpoint_type
            if "lowf" in endpoint_type:
                scenario['feel_level'] = 'Low'
            elif "highf" in endpoint_type:
                scenario['feel_level'] = 'High'
            else:
                scenario['feel_level'] = 'High'  # default
            
            # Set think level based on endpoint_type
            if "lowt" in endpoint_type:
                scenario['think_level'] = 'Low'
            elif "hight" in endpoint_type:
                scenario['think_level'] = 'High'
            else:
                scenario['think_level'] = 'High'  # default
            
            # Store scenario in session
            request.session['scenario'] = scenario
            request.session.save()  # Explicitly save the session
            safe_debug_print(f"DEBUG: Set scenario for main endpoint {endpoint_type}: {scenario}")
            
            return Response({
                "endpoint": f"/api/random/",
                "endpoint_type": endpoint_type
            })

    def post(self, request, *args, **kwargs):
        # Handle POST requests (main chat functionality)
        
        try:
            # Get scenario from session - if it doesn't exist, that's a problem
            scenario = request.session.get('scenario')
            if scenario:
                safe_debug_print(f"DEBUG: POST request - using existing scenario: {scenario}")
            else:
                # Fallback scenario - this should rarely be needed
                scenario = {
                    'brand': 'error',
                    'problem_type': 'error',
                    'think_level': 'error',
                    'feel_level': 'error'
                }
            
            # Use scenario brand to determine which view to use
            if scenario['brand'] == 'Lulu':
                # Use the Lulu API view
                lulu_view = LuluAPIView()
                return lulu_view.post(request, *args, **kwargs)
            else:
                # Use the general API view
                general_view = ChatAPIView()
                response = general_view.post(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
                
        except Exception as e:
            safe_debug_print(f"ERROR in RandomEndpointAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)