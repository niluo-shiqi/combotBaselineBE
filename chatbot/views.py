from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from transformers import pipeline
from django.utils.safestring import mark_safe
from .models import Conversation
from transformers import pipeline
import random
import json
import openai
import os


openai.api_key = os.getenv('OPENAI_API_KEY')

class ChatAPIView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        user_input = data.get('message', '')
        conversation_index = data.get('index', 0)
        time_spent = data.get('timer', 0)
        chat_log = data.get('chatLog', '')
        class_type = data.get('classType', '')
        message_type_log = data.get('messageTypeLog', '')
        
        # Get the scenario information from the session
        scenario = request.session.get('scenario', {
            'brand': 'Basic',
            'problem_type': 'A',
            'think_level': 'High',
            'feel_level': 'High'
        })

        if conversation_index in (0, 1, 2, 3, 4):
            if conversation_index == 0:
                os.environ["TRANSFORMERS_CACHE"] = "./cache"  # Optional, for local storage
                os.environ["USE_TF"] = "0"  # Disable TensorFlow
                classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier", from_pt=True)
                class_response = classifier(user_input)[0]
                class_type = class_response["label"]
                confidence = class_response["score"]
                if class_type == "Other":
                    conversation_index += 10
                chat_response = self.question_initial_response(class_type, user_input, scenario)
                message_type = scenario['think_level']
                if chat_response.startswith("Paraphrased: "):
                    message_type = "Low"
                    chat_response = chat_response[len("Paraphrased: "):]
                message_type += class_type
            elif conversation_index in (1, 2, 3, 4):
                second_message_text = message_type_log[1]['text']

                if "Low" in second_message_text:
                    chat_response = self.low_question_continuation_response(chat_log)
                    message_type = " "
                else:
                    chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                    message_type = " "

        elif conversation_index == 5:
            chat_response, message_type = self.understanding_statement_response(scenario)
        elif conversation_index == 6:
            chat_response = self.save_conversation(user_input, time_spent, chat_log, message_type_log, scenario)
            message_type = " "
        else:
            chat_response = " "
            message_type = " "

        conversation_index += 1
        return Response({"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}, status=status.HTTP_200_OK)

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
            chat_response = completion["choices"][0]["message"]["content"] + "meow"

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

        return chat_response

    def low_question_continuation_response(self, chat_log):
        chat_logs_string = json.dumps(chat_log, indent=2)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "I am going to supply you a chat log. Add only the next response as " +
                                                           "though you are boring to talk to. The premise is that you are an " +
                                                           "unhelpful customer service chat bot. Whatever your response is, " +
                                                           "make it a response that the customer will want to reply to. You" +
                                                           "can make your response a question or a statement. " +
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
        feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect."
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input):
        print("This is the user_input: ", user_input)
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: " + user_input}],
        )
        return completion["choices"][0]["message"]["content"] + "woof"

    def paraphrase_response(self, user_input):
        print("Wow is the user_input: ", user_input)
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "Pretend you're a customer service bot. Paraphrase what I am about to say in the next sentence" +
                                                       "then ask me to elaborate or how I wish to resolve this issue." + user_input}],
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"] + "123!"

    def save_conversation(self, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        conversation = Conversation(
            email=email,
            time_spent=time_spent,
            chat_log=chat_log,
            message_type_log=message_type_log,
            test_type=scenario['brand'],
            problem_type=scenario['problem_type'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level']
        )
        conversation.save()

        html_message = mark_safe(
            "Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: "
            "<a href='https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE' target='_blank' rel='noopener noreferrer'>Survey Link</a>."
        )

        return html_message


class InitialMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # For general endpoint, only use Basic brand
        brand = "Basic"
        problem_type = random.choice(["A", "B", "C"])
        think_level = random.choice(["High", "Low"])
        feel_level = random.choice(["High", "Low"])
        
        # Store the scenario assignment in the session
        request.session['scenario'] = {
            'brand': brand,
            'problem_type': problem_type,
            'think_level': think_level,
            'feel_level': feel_level
        }
        
        # Get the appropriate initial message based on brand and think level

    
        if think_level == "High":
            initial_message = {
                "message": "[Basic high endpoint]Hi there! I'm Combot, and it's great to meet you. I'm here to help with any product or " +
                            "service problems you may have encountered in the past few months. This could include issues like " +
                            "a defective product, a delayed package, or a rude employee. My goal is to provide you with the best " +
                            "guidance to resolve your issue. Please start by recounting your bad experiences with as many " +
                            "details as possible (when, how, and what happened). " +
                            "While I specialize in handling these issues, I am not Alexa or Siri. " +
                            "Let's work together to resolve your problem!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "[Basic low endpoint]The purpose of Combot is to assist you with any product or service problems you have " +
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
                "problem_type": problem_type,
                "think_level": think_level,
                "feel_level": feel_level
            }
        }

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
        # For general endpoint, only use Basic brand
        brand = "Lulu"
        problem_type = random.choice(["A", "B", "C"])
        think_level = random.choice(["High", "Low"])
        feel_level = random.choice(["High", "Low"])
        
        # Store the scenario assignment in the session
        request.session['scenario'] = {
            'brand': brand,
            'problem_type': problem_type,
            'think_level': think_level,
            'feel_level': feel_level
        }
        if think_level == "High":
            initial_message = {
                "message": "[LULU ENDPOINT] Hi there! I'm Combot, and it's great to meet you. I'm here to help with any product or " +
                            "service problems you may have encountered in the past few months. My goal is to make sure you receive " +
                            "the best guidance from me. Let's work together to resolve your issue!"
            }
        elif think_level == "Low":
            initial_message = {
                "message": "[LULU ENDPOINT] The purpose of Combot is to assist with resolution of product/service problems. " +
                            "If you have experienced any issues in the past few months, Combot is designed to guide you through " +
                            "finding the optimal solution."
            }


        # Include all scenario information in the response
        response_data = {
            "message": initial_message['message'],
            "scenario": {
                "brand": brand,
                "problem_type": problem_type,
                "think_level": think_level,
                "feel_level": feel_level
            }
        }
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

        if conversation_index in (0, 1, 2, 3, 4):
            if conversation_index == 0:
                classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier", from_pt=True)
                class_response = classifier(user_input)[0]
                class_type = class_response["label"]
                confidence = class_response["score"]
                if class_type == "Other":
                    conversation_index += 10
                chat_response = self.question_initial_response(class_type, user_input)
                message_type = "High"
                if chat_response.startswith("Paraphrased: "):
                    message_type = "Low"
                    chat_response = chat_response[len("Paraphrased: "):]
                message_type += class_type
            elif conversation_index in (1, 2, 3, 4):

                second_message_text = message_type_log[1]['text']

                if "Low" in second_message_text:
                    chat_response = self.low_question_continuation_response(chat_log)

                    message_type = " "
                else:
                    chat_response = self.high_question_continuation_response(class_type, chat_log)

                    message_type = " "

        elif conversation_index == 5:
            chat_response, message_type = self.understanding_statement_response()
        elif conversation_index == 6:
            chat_response = self.save_conversation(user_input, time_spent, chat_log, message_type_log)
            message_type = " "
        else:
            chat_response = " "
            message_type = " "

        conversation_index += 1
        return Response({"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}, status=status.HTTP_200_OK)

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
                messages=[{"role": "assistant", "content": "You are a customer service bot. Paraphrase the following customer complaint back to them then ask them to provide more information. Here's the complaint: " + user_input}],
            )
            chat_response = completion["choices"][0]["message"]["content"] + "woof"

        return chat_response

    def high_question_continuation_response(self, class_type, chat_log):

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

        return chat_response

    def low_question_continuation_response(self, chat_log):
        chat_logs_string = json.dumps(chat_log, indent=2)
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "assistant", "content": "I am going to supply you a chat log. Add only the next response as " +
                                                           "though you are boring to talk to. The premise is that you are an " +
                                                           "unhelpful customer service chat bot. Whatever your response is, " +
                                                           "make it a response that the customer will want to reply to. You" +
                                                           "can make your response a question or a statement. " +
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

    def understanding_statement_response(self):
        understanding_statement = "I understand your situation and I want to help you resolve this issue. " + \
                                 "I have gathered all the necessary information to provide you with the best possible solution. " + \
                                 "Let me work on finding the most appropriate resolution for your case."
        return understanding_statement, "Understanding"

    def conversation_index_10_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "You are a customer service bot. Paraphrase the following customer complaint and ask them to provide more information. Here's the complaint: " + user_input}],
        )
        return completion["choices"][0]["message"]["content"] + "woof"

    def paraphrase_response(self, user_input):
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "assistant", "content": "Pretend you're a customer service bot. Paraphrase what I am about to say in the next sentence" +
                                                       "then ask me to elaborate or I wish to resolve this issue." + user_input}],
        )
        return "Paraphrased: " + completion["choices"][0]["message"]["content"] + "123!"

    def save_conversation(self, email, time_spent, chat_log, message_type_log):
        # Get the endpoint type from session
        endpoint_type = request.session.get('endpoint_type', 'lulu')
        
        conversation = Conversation.objects.create(
            email=email,
            time_spent=time_spent,
            chat_log=chat_log,
            message_type_log=message_type_log,
            test_type="Lulu",
            problem_type="A",
            think_level="High",
            feel_level="High",
            endpoint_type=endpoint_type
        )
        return "Thank you for sharing your experience with me! I will send you a set of comprehensive suggestions via email. Please provide your email below..."


class RandomEndpointAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Get the path to determine which endpoint this is
        path = request.path
        
        if path.endswith('/initial/'):
            # Handle initial message request
            endpoint_type = random.choice(['general', 'lulu'])
            request.session['endpoint_type'] = endpoint_type
            
            if endpoint_type == 'general':
                # Use the general initial message view
                initial_view = InitialMessageAPIView()
                return initial_view.get(request, *args, **kwargs)
            else:
                # Use the Lulu initial message view
                lulu_initial_view = LuluInitialMessageAPIView()
                return lulu_initial_view.get(request, *args, **kwargs)
        
        elif path.endswith('/closing/'):
            # Handle closing message request
            endpoint_type = request.session.get('endpoint_type', 'general')
            
            if endpoint_type == 'lulu':
                # Use the Lulu closing message view
                lulu_closing_view = LuluClosingMessageAPIView()
                return lulu_closing_view.get(request, *args, **kwargs)
            else:
                # Use the general closing message view
                closing_view = ClosingMessageAPIView()
                return closing_view.get(request, *args, **kwargs)
        
        else:
            # Handle main endpoint request
            endpoint_type = random.choice(['general', 'lulu'])
            request.session['endpoint_type'] = endpoint_type
            
            return Response({
                "endpoint": f"/api/{endpoint_type}/",
                "endpoint_type": endpoint_type
            })

    def post(self, request, *args, **kwargs):
        # Handle POST requests (main chat functionality)
        endpoint_type = request.session.get('endpoint_type', 'general')
        
        if endpoint_type == 'lulu':
            # Use the Lulu API view
            lulu_view = LuluAPIView()
            return lulu_view.post(request, *args, **kwargs)
        else:
            # Use the general API view
            general_view = ChatAPIView()
            return general_view.post(request, *args, **kwargs)