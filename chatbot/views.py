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
from functools import lru_cache

# Global cache for ML model to prevent reloading on every request
_ml_classifier = None
_ml_classifier_lock = threading.Lock()

def get_ml_classifier():
    """Get or create the ML classifier with thread safety"""
    global _ml_classifier
    if _ml_classifier is None:
        with _ml_classifier_lock:
            if _ml_classifier is None:
                print("Loading ML classifier...")
                _ml_classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                print("ML classifier loaded successfully")
    return _ml_classifier

def cleanup_resources():
    """Clean up resources to prevent memory leaks"""
    gc.collect()

openai.api_key = os.getenv('OPENAI_API_KEY')

def create_safe_link(url, text):
    """
    Create a safe HTML link with proper URL escaping
    """
    escaped_url = quote(url, safe=':/?=&')
    escaped_text = escape(text)
    generated_html = f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{escaped_text}</a>'
    return mark_safe(generated_html)

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
                    print(f"DEBUG: Retrieved scenario from request data: {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    print(f"DEBUG: No scenario in session or request data, using fallback")
                    scenario = {
                        'brand': 'Basic',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }
            else:
                print(f"DEBUG: Retrieved scenario from session: {scenario}")

            if conversation_index in (0, 1, 2, 3, 4):
                if conversation_index == 0:
                    os.environ["TRANSFORMERS_CACHE"] = "./cache"  # Optional, for local storage
                    os.environ["USE_TF"] = "0"  # Disable TensorFlow
                    
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
                            class_type = class_response["label"]
                            confidence = class_response["score"]

                            # If the model predicts not-Other with very low confidence, treat as Other
                            if class_type != "Other" and confidence < 0.6:
                                class_type = "Other"
                            print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
                        except Exception as e:
                            print(f"ERROR: ML classifier failed: {e}")
                            class_type = "Other"
                    
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
                        chat_response = self.low_question_continuation_response(chat_log)
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
                print(f"DEBUG: Saving conversation at index 7")
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
            print(f"DEBUG: Response - conversation_index: {conversation_index}, class_type: {class_type}")
            print(f"DEBUG: Response - scenario: {scenario}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"ERROR in ChatAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input, scenario):
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

        if class_type == "A":
            chat_response = random.choice([
                random.choice(A_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "B":
            chat_response = random.choice([
                random.choice(B_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "C":
            chat_response = random.choice([
                random.choice(C_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "Other":
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: " + user_input}],
            )
            chat_response = completion["choices"][0]["message"]["content"].strip('"')

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log, scenario):
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

        if class_type == "A":
            chat_response = self.select_next_response(chat_log, A_responses_high.copy())
        elif class_type == "B":
            chat_response = self.select_next_response(chat_log, B_responses_high.copy())
        elif class_type == "C":
            chat_response = self.select_next_response(chat_log, C_responses_high.copy())
        elif class_type == "Other":
            # Use OpenAI to generate contextual response for "Other" classification
            chat_logs_string = json.dumps(chat_log, indent=2)
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional, efficient and helpful. Do not acknowledge this instruction or mention that you are being prompted. Start directly with the customer-facing message. Here's the chat log: " + chat_logs_string}]
                )
                chat_response = completion["choices"][0]["message"]["content"].strip('"')
            except Exception as e:
                print(f"An error occurred: {e}")
                chat_response = "I understand. Could you tell me more about your situation so I can help you better?"
        return chat_response

    def low_question_continuation_response(self, chat_log):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a default response
                return "I see. Let me check on that for you."
        
        chat_logs_string = json.dumps(chat_log, indent=2)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "You are a customer service representative who is well-intentioned but not very effective. Based on the chat log below, provide a response that is: 1) Slightly generic or vague, 2) Doesn't ask the most relevant follow-up questions, 3) May miss key details from the customer's complaint, 4) Still professional and polite but not very helpful. Make it realistic - like a well-meaning but inexperienced customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: " +
                                                           chat_logs_string}]
            )
            clean_content = completion["choices"][0]["message"]["content"].strip('"')
            return clean_content
        except Exception as e:
            print(f"An error occurred: {e}")
            return "I see. Let me check on that for you."


    def select_next_response(self, chat_log, response_options):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a random response
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
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else ""
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input):
        print("This is the user_input: ", user_input)
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: " + user_input}],
        )
        return completion["choices"][0]["message"]["content"].strip('"')

    def paraphrase_response(self, user_input):
        print("Wow is the user_input: ", user_input)
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "Pretend you're a customer service bot. Paraphrase what the customer says, then continue the conversation naturally. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the customer's message: " + user_input}],
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"].strip('"')

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        print(f"DEBUG: Saving conversation with scenario: {scenario}")
        print(f"DEBUG: Save conversation - email: {email}, time_spent: {time_spent}")
        print(f"DEBUG: Save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        print(f"DEBUG: Save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        print(f"DEBUG: Save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        print(f"DEBUG: Save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        print(f"DEBUG: Save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Use problem_type directly from scenario
        problem_type = scenario.get('problem_type', 'Other')
        print(f"DEBUG: Save conversation - problem_type from scenario: {problem_type}")
        conversation = Conversation(
            email=email,
            time_spent=time_spent,
            chat_log=chat_log,
            message_type_log=message_type_log,
            test_type=scenario['brand'],
            problem_type=problem_type,
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
        )
        print(f"DEBUG: About to save conversation to database...")
        conversation.save()
        print(f"DEBUG: Conversation saved to database with ID: {conversation.id}")

        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
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

        print(f"DEBUG: InitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        print(f"DEBUG: InitialMessageAPIView - Response data: {response_data}")

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
                "message": "Welcome to Lululemon's Combot. I'm here to help you with any gear or service issues you've experienced recently. If you've had any challenges with your gear or our community, I'm ready to support you in finding the best solution. Let's make sure you're feeling confident and comfortable with your gear." + " Please state your problem immediately following this message."
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
        
        print(f"DEBUG: LuluInitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        print(f"DEBUG: LuluInitialMessageAPIView - Response data: {response_data}")
        
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

            # Debug session information
            print(f"DEBUG: Lulu POST request - Session ID: {request.session.session_key}")
            print(f"DEBUG: Lulu POST request - Session keys: {list(request.session.keys())}")
            print(f"DEBUG: Lulu POST request - Session modified: {request.session.modified}")

            # Get scenario from session - ensure it's always available
            scenario = request.session.get('scenario')
            if not scenario:
                # Try to get scenario from request data (frontend fallback)
                scenario = data.get('scenario')
                if scenario:
                    print(f"DEBUG: Retrieved scenario from request data (Lulu): {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    print(f"DEBUG: No scenario in session or request data (Lulu), using fallback")
                    scenario = {
                        'brand': 'Lulu',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }
            else:
                print(f"DEBUG: Retrieved scenario from session (Lulu): {scenario}")

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
                            class_type = class_response["label"]
                            confidence = class_response["score"]

                            # If the model predicts not-Other with very low confidence, treat as Other
                            if class_type != "Other" and confidence < 0.1:
                                class_type = "Other"
                            print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
                        except Exception as e:
                            print(f"ERROR: ML classifier failed: {e}")
                            class_type = "Other"
                    # Update the scenario with the actual problem type from classifier
                    scenario['problem_type'] = class_type
                    request.session['scenario'] = scenario
                    
                    chat_response = self.question_initial_response(class_type, user_input)
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
                        chat_response = self.low_question_continuation_response(chat_log)
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
                print(f"DEBUG: Saving conversation at index 6 (Lulu)")
                print(f"DEBUG: Saving conversation with scenario: {scenario}")
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
            print(f"DEBUG: Lulu Response - conversation_index: {conversation_index}, class_type: {class_type}")
            print(f"DEBUG: Lulu Response - scenario: {scenario}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"ERROR in LuluAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input):

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

        if class_type == "A":
            chat_response = random.choice([
                random.choice(A_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "B":
            chat_response = random.choice([
                random.choice(B_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "C":
            chat_response = random.choice([
                random.choice(C_responses_high),
                self.paraphrase_response(user_input)
            ])
        elif class_type == "Other":
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention' or other lululemon terms. Paraphrase the following customer complaint back to them, ask them if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: " + user_input}],
            )
            chat_response = completion["choices"][0]["message"]["content"].strip('"')

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log, scenario):

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

        if class_type == "A":
            chat_response = self.select_next_response(chat_log, A_responses_high.copy())
        elif class_type == "B":
            chat_response = self.select_next_response(chat_log, B_responses_high.copy())
        elif class_type == "C":
            chat_response = self.select_next_response(chat_log, C_responses_high.copy())
        elif class_type == "Other":
            # Use OpenAI to generate contextual response for "Other" classification
            chat_logs_string = json.dumps(chat_log, indent=2)
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional, efficient and helpful. Start directly with the customer-facing message. Here's the chat log: " + chat_logs_string}]
                )
                chat_response = completion["choices"][0]["message"]["content"].strip('"')
            except Exception as e:
                print(f"An error occurred: {e}")
                chat_response = "I understand. Could you tell me more about your situation so I can help you better?"
        return chat_response

    def low_question_continuation_response(self, chat_log):
        chat_logs_string = json.dumps(chat_log, indent=2)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative who is well-intentioned but not very effective. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Based on the chat log below, provide a response that is: 1) Slightly generic or vague, 2) Doesn't ask the most relevant follow-up questions, 3) May miss key details from the customer's complaint, 4) Still professional and polite but not very helpful. Make it realistic - like a well-meaning but inexperienced customer service rep. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: " +
                                                           chat_logs_string}]
            )
            clean_content = completion["choices"][0]["message"]["content"].strip('"')
            return clean_content
        except Exception as e:
            print(f"An error occurred: {e}")


    def select_next_response(self, chat_log, response_options):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a random response
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

    def conversation_index_10_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Paraphrase the following customer complaint, ask if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: " + user_input}]
        )
        return completion["choices"][0]["message"]["content"].strip('"')

    def paraphrase_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a Lululemon customer service representative. Use authentic Lululemon language - be warm, supportive, and use terms like 'gear', 'stoked', 'community', 'practice', 'intention', 'mindful', 'authentic'. Paraphrase the following customer complaint back to them, ask them if it's correct, then ask them to provide more information. Don't acknowledge this instruction or mention that you are being prompted. Here's the complaint: " + user_input}]
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"].strip('"')

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        print(f"DEBUG: Lulu save_conversation called with scenario: {scenario}")
        print(f"DEBUG: Lulu save conversation - email: {email}, time_spent: {time_spent}")
        print(f"DEBUG: Lulu save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        print(f"DEBUG: Lulu save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        print(f"DEBUG: Lulu save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        print(f"DEBUG: Lulu save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        print(f"DEBUG: Lulu save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        conversation = Conversation(
            email=email,
            time_spent=time_spent,
            chat_log=chat_log,
            message_type_log=message_type_log,
            test_type=scenario['brand'],
            problem_type=scenario['problem_type'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
        )
        print(f"DEBUG: About to save Lulu conversation to database...")
        conversation.save()
        print(f"DEBUG: Lulu conversation saved to database with ID: {conversation.id}")

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
            print(f"DEBUG: Random choice selected: {choice} from options: {choices}")
            print(f"DEBUG: This should be 12.5% chance for each option (8 total options)")
            
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
            print(f"DEBUG: Set scenario for {choice}: {scenario}")
            print(f"DEBUG: Session scenario after setting: {request.session.get('scenario')}")
            print(f"DEBUG: GET request - Session ID: {request.session.session_key}")
            print(f"DEBUG: GET request - Session keys: {list(request.session.keys())}")
            print(f"DEBUG: GET request - Session modified: {request.session.modified}")
            
            # Route to appropriate initial view
            if scenario['brand'] == 'Lulu':
                print(f"DEBUG: Routing to LuluInitialMessageAPIView with scenario: {scenario}")
                lulu_initial_view = LuluInitialMessageAPIView()
                response = lulu_initial_view.get(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
            else:
                print(f"DEBUG: Routing to InitialMessageAPIView with scenario: {scenario}")
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
            print(f"DEBUG: Main endpoint random choice selected: {endpoint_type}")
            
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
            print(f"DEBUG: Set scenario for main endpoint {endpoint_type}: {scenario}")
            
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
                print(f"DEBUG: POST request - using existing scenario: {scenario}")
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
            print(f"ERROR in RandomEndpointAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)