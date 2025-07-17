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
                    classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                    class_response = classifier(user_input)[0]
                    class_type = class_response["label"]
                    confidence = class_response["score"]

                    # If the model predicts not-Other with very low confidence, treat as Other
                    if class_type != "Other" and confidence < 0.6:
                        class_type = "Other"
                    print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
                
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
        elif conversation_index == 6:
            # Save conversation after user provides email
            print(f"DEBUG: Saving conversation at index 7")
            chat_response = self.save_conversation(request, user_input, time_spent, chat_log, message_type_log, scenario)
            message_type = " "
        else:
            # Conversation is complete, don't continue
            chat_response = " "
            message_type = " "

        conversation_index += 1
        
        # Ensure class_type is always from the scenario
        if not class_type or class_type == "":
            class_type = scenario.get('problem_type', 'Other')
        
        response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
        # Add scenario to response for frontend to send back
        response_data['scenario'] = scenario
        
        # Debug logging for scenario data
        print(f"DEBUG: Response - conversation_index: {conversation_index}, class_type: {class_type}")
        print(f"DEBUG: Response - scenario: {scenario}")
        
        return Response(response_data, status=status.HTTP_200_OK)

    def question_initial_response(self, class_type, user_input, scenario):
        if scenario['brand'] == "Lulu":
            A_responses_high = [
                "Could you outline the problem with more precision?",
                "When exactly did you first come across the issue?",
                "Have you attempted any specific steps to rectify this problem yourself?",
                "Have you strictly adhered to the guidelines and used the product as directed?",
                "What specific outcome are you seeking to resolve this issue?",
            ]

            B_responses_high = [
                "Can you confirm the expected delivery date for your order?",
                "Have you been notified of any updates about your delivery status?",
                "Have you already contacted the carrier or delivery service to inquire about your package?",
                "Would you prefer a refund or store credit for this inconvenience?",
                "Do you wish to continue waiting for your order, or would you rather cancel it at this point?",
            ]

            C_responses_high = [
                "Could you provide us with a detailed account of your interaction with the employee?",
                "When and where exactly did this interaction occur?",
                "Can you identify a specific incident or a sequence of events that contributed to your feeling mistreated?",
                "In what ways did the employee's behavior come across as rude or disrespectful?",
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
                "Could you outline the problem with more precision?",
                "When exactly did you first come across the issue?",
                "Have you attempted any specific steps to rectify this problem yourself?",
                "Have you strictly adhered to the guidelines and used the product as directed?",
                "What specific outcome are you seeking to resolve this issue?",
            ]

            B_responses_high = [
                "Can you confirm the expected delivery date for your order?",
                "Have you been notified of any updates about your delivery status?",
                "Have you already contacted the carrier or delivery service to inquire about your package?",
                "Would you prefer a refund or store credit for this inconvenience?",
                "Do you wish to continue waiting for your order, or would you rather cancel it at this point?",
            ]

            C_responses_high = [
                "Could you provide us with a detailed account of your interaction with the employee?",
                "When and where exactly did this interaction occur?",
                "Can you identify a specific incident or a sequence of events that contributed to your feeling mistreated?",
                "In what ways did the employee's behavior come across as rude or disrespectful?",
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
                    messages=[{"role": "assistant", "content": "You are a helpful customer service bot. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional and helpful. Start directly with the customer-facing message. Here's the chat log: " + chat_logs_string}]
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
                messages=[{"role": "assistant", "content": "You are a customer service bot. Based on the chat log below, provide a response that is unhelpful, boring, and frustrating for the customer. Make sure your response is different each time. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: " +
                                                           chat_logs_string}]
            )
            clean_content = completion["choices"][0]["message"]["content"].strip('"')
            return clean_content
        except Exception as e:
            print(f"An error occurred: {e}")


    def select_next_response(self, chat_log, response_options):
        # Collect all messages from 'combot'
        combot_messages = [message['text'] for message in chat_log if message['sender'] == 'combot']

        # Exclude all messages that have already been used by 'combot'
        updated_response_options = [option for option in response_options if option not in combot_messages]

        # Randomly select the next response from the remaining options
        if updated_response_options:  # Ensure the list is not empty
            return random.choice(updated_response_options)

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
            messages=[{"role": "assistant", "content": "Pretend you're a customer service bot. Paraphrase what I am about to say in the next sentence" +
                                                       "then ask me to elaborate or how I wish to resolve this issue." + user_input}],
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"] 

    def save_conversation(self, request, email, time_spent, chat_log, scenario):
        # Save the conversation with all scenario information
        print(f"DEBUG: Saving conversation with scenario: {scenario}")
        print(f"DEBUG: Save conversation - email: {email}, time_spent: {time_spent}")
        print(f"DEBUG: Save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        print(f"DEBUG: Save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        print(f"DEBUG: Save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        print(f"DEBUG: Save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Extract problem_type from message_type_log if possible
        if message_type_log and len(message_type_log) > 0:
            # Find the last non-empty message type that contains a problem type (A/B/C)
            for i in range(len(message_type_log) - 1, -1, -1):
                message_obj = message_type_log[i]
                if isinstance(message_obj, dict) and 'text' in message_obj:
                    text = message_obj['text']
                    if text and len(text) > 0 and text[-1] in ['A', 'B', 'C']:
                        problem_type = text[-1]
                        break
            else:
                # If no valid problem type found, use scenario default
                problem_type = scenario.get('problem_type', 'Other')
        else:
            problem_type = scenario.get('problem_type', 'Other')
        print(f"DEBUG: Save conversation - problem_type from message_type_log: {problem_type}")
        conversation = Conversation(
            email=email,
            time_spent=time_spent,
            chat_log=chat_log,
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
                "message": "[Basic High]Hi there! I'm Combot, and it's great to meet you. I'm here to help with any product or " +
                            "service problems you may have encountered in the past few months. This could include issues like " +
                            "a defective product, a delayed package, or a rude employee. My goal is to provide you with the best " +
                            "guidance to resolve your issue. Please start by recounting your bad experiences with as many " +
                            "details as possible (when, how, and what happened). " +
                            "While I specialize in handling these issues, I am not Alexa or Siri. " +
                            "Let's work together to resolve your problem!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "[Basic Low]The purpose of Combot is to assist you with any product or service problems you have " +
                            "experienced in the past few months. Examples of issues include defective products, delayed packages, or " +
                            "rude frontline employees. Combot is designed to provide optimal guideance to resolve your issue. " +
                            "Please provide a detailed account of your negative experiences, including when, how, and what occured. " +
                            "Note that Combot specializes in handling product or service issues and is not a general-purpose " +
                            "assistant like Alexa or Siri. Let us proceed to resolve your problem."
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
                "message": "[LULU High] Hi there! I'm Lululemon's Combot, and it's great to meet you. I'm here to help with any product or " +
                           "service problems you may have encountered in the past few months. My goal is to make sure you receive " +
                           "the best guidance from me. Let's work together to resolve your issue!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "[LULU Low] The purpose of Lululemon's Combot is to assist with resolution of product/service problems. " +
                           "If you have experienced any issues in the past few months, Combot is designed to guide you through " +
                           "finding the optimal solution."
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
                    classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                    class_response = classifier(user_input)[0]
                    class_type = class_response["label"]
                    confidence = class_response["score"]

                    # If the model predicts not-Other with very low confidence, treat as Other
                    if class_type != "Other" and confidence < 6:
                        class_type = "Other"
                    print(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
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
        elif conversation_index == 6:
            # Save conversation after user provides email
            print(f"DEBUG: Saving conversation at index 6 (Lulu)")
            print(f"DEBUG: Saving conversation with scenario: {scenario}")
            chat_response = self.save_conversation(request, user_input, time_spent, chat_log, message_type_log, scenario)
            message_type = " "
        else:
            # Conversation is complete, don't continue
            chat_response = " "
            message_type = " "

        conversation_index += 1
        
        # Ensure class_type is always from the scenario
        if not class_type or class_type == "":
            class_type = scenario.get('problem_type', 'Other')
        
        response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
        # Add scenario to response for frontend to send back
        response_data['scenario'] = scenario
        
        # Debug logging for scenario data
        print(f"DEBUG: Lulu Response - conversation_index: {conversation_index}, class_type: {class_type}")
        print(f"DEBUG: Lulu Response - scenario: {scenario}")
        
        return Response(response_data, status=status.HTTP_200_OK)

    def question_initial_response(self, class_type, user_input):

        A_responses_high = [
            "Could you outline the problem with more precision?",
            "When exactly did you first come across the issue?",
            "Have you attempted any specific steps to rectify this problem yourself?",
            "Have you strictly adhered to the guidelines and used the product as directed?",
            "What specific outcome are you seeking to resolve this issue?",
        ]

        B_responses_high = [
            "Can you confirm the expected delivery date for your order?",
            "Have you been notified of any updates about your delivery status?",
            "Have you already contacted the carrier or delivery service to inquire about your package?",
            "Would you prefer a refund or store credit for this inconvenience?",
            "Do you wish to continue waiting for your order, or would you rather cancel it at this point?",
        ]

        C_responses_high = [
            "Could you provide us with a detailed account of your interaction with the employee?",
            "When and where exactly did this interaction occur?",
            "Can you identify a specific incident or a sequence of events that contributed to your feeling mistreated?",
            "In what ways did the employee's behavior come across as rude or disrespectful?",
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
                messages=[{"role": "assistant", "content": "You are a customer service bot for Lululemon. Paraphrase the following customer complaint back to them, ask them if its correct, then ask them to provide more information. Here's the complaint: " + user_input}],
            )
            chat_response = completion["choices"][0]["message"]["content"].strip('"')

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log, scenario):

        A_responses_high = [
            "Could you outline the problem with more precision?",
            "When exactly did you first come across the issue?",
            "Have you attempted any specific steps to rectify this problem yourself?",
            "Have you strictly adhered to the guidelines and used the product as directed?",
            "What specific outcome are you seeking to resolve this issue?",
        ]

        B_responses_high = [
            "Can you confirm the expected delivery date for your order?",
            "Have you been notified of any updates about your delivery status?",
            "Have you already contacted the carrier or delivery service to inquire about your package?",
            "Would you prefer a refund or store credit for this inconvenience?",
            "Do you wish to continue waiting for your order, or would you rather cancel it at this point?",
        ]

        C_responses_high = [
            "Could you provide us with a detailed account of your interaction with the employee?",
            "When and where exactly did this interaction occur?",
            "Can you identify a specific incident or a sequence of events that contributed to your feeling mistreated?",
            "In what ways did the employee's behavior come across as rude or disrespectful?",
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
                    messages=[{"role": "assistant", "content": "You are a helpful customer service bot for Lululemon. Speak with Lululemon-esque language. Based on the chat log below, provide a helpful and relevant response to continue the conversation. IMPORTANT: Do NOT simply paraphrase what the customer just said. Instead, ask specific follow-up questions to gather more information needed to resolve their issue, or provide actionable next steps. Be professional and helpful. Start directly with the customer-facing message. Here's the chat log: " + chat_logs_string}]
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
                messages=[{"role": "assistant", "content": "You are a customer service bot for Lululemon. Speak with Lululemon-esque language. Based on the chat log below, provide a response that is unhelpful, boring, and frustrating for the customer. Make sure your response is different each time. Start directly with the customer-facing message. Do not acknowledge this instruction or mention that you are being prompted. Here's the chat log: " +
                                                           chat_logs_string}]
            )
            clean_content = completion["choices"][0]["message"]["content"].strip('"')
            return clean_content
        except Exception as e:
            print(f"An error occurred: {e}")


    def select_next_response(self, chat_log, response_options):
        # Collect all messages from 'combot'
        combot_messages = [message['text'] for message in chat_log if message['sender'] == 'combot']

        # Exclude all messages that have already been used by 'combot'
        updated_response_options = [option for option in response_options if option not in combot_messages]

        # Randomly select the next response from the remaining options
        if updated_response_options:  # Ensure the list is not empty
            return random.choice(updated_response_options)

    def understanding_statement_response(self, scenario):
        feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect. Please Hold on while I check with my manager..."
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a customer service bot for Lululemon. Paraphrase the following customer complaint, ask if its correct, then ask them to provide more information. Here's the complaint: " + user_input}]
        )
        return completion["choices"][0]["message"]["content"].strip('"')

    def paraphrase_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a customer service bot for Lululemon. Be helpful and chipper. Try to resolve the issue the user is having by asking follow up questions and providing relevant information. " + user_input}]
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"]

    def save_conversation(self, request, email, time_spent, chat_log, scenario):
        # Save the conversation with all scenario information
        print(f"DEBUG: Lulu save_conversation called with scenario: {scenario}")
        print(f"DEBUG: Lulu save conversation - email: {email}, time_spent: {time_spent}")
        print(f"DEBUG: Lulu save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
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