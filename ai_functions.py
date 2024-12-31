from openai import OpenAI
import streamlit as st

@st.cache_resource
def get_client():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    return client

def chat_prompt_json(prompt_text, system_prompt, max_tokens, json_type):
    prompt = {
        "model": "gpt-4o",
        "messages": [
            {
            "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt_text[0],
            },
        ],
        "max_tokens": max_tokens
    }

    client = get_client()

    # Call OpenAI to generate monsters
    completion = client.beta.chat.completions.parse(**prompt, response_format=json_type)
    response = completion.choices[0].message.parsed
    return response

def chat_prompt(prompt_text, system_prompt, max_tokens):
    prompt = {
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ],
        "max_tokens": max_tokens
    }

    client = get_client()

    # Call OpenAI to generate room details
    completion = client.chat.completions.create(**prompt)
    response = completion.choices[0].message.content
    return response