from together import Together
from typing import List, Dict
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_llm_response(chat_history: List[Dict[str, str]], references: List[str]) -> str:
    """
    Generate a response using the Together API with the given chat history and references.

    Args:
    chat_history (List[Dict[str, str]]): List of previous messages in the chat.
    references (List[str]): List of possible references to include in the prompt.

    Returns:
    str: The generated response from the LLM.
    """
    # Get the API key from the environment variable
    api_key = os.getenv('TOGETHER_API_KEY')

    if not api_key:
        raise ValueError("TOGETHER_API_KEY not found in environment variables")

    client = Together(api_key=api_key)

    # Prepare the messages for the API call
    messages = chat_history.copy()

    # Add references to the last user message if available
    if references and messages[-1]['role'] == 'user':
        reference_text = "\n\nReferences:\n" + "\n".join(references)
        messages[-1]['content'] += reference_text

    try:
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>","<|eom_id|>"],
            stream=True
        )

        # Collect the streamed response
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'choices'):
                full_response += chunk.choices[0].delta.content or ""

        return full_response.strip()

    except Exception as e:
        print(f"Error calling Together API: {str(e)}")
        return ""

# Example usage:
if __name__ == "__main__":
    chat_history = [
        {"role": "user", "content": "Hvernig er veðrið venjulega á Íslandi á veturna?"},
        {"role": "assistant", "content": "Veðrið á Íslandi á veturna er venjulega kalt og óstöðugt. Hér eru nokkrar einkennandi áherslur:\n\n1. Kalt: Meðalhiti á Íslandi á veturna er um 2-5°C í láglendi, en getur verið miklu kaldara í fjöllum.\n2. Vind: Vetrarvindar á Íslandi eru oftast miklir og geta verið stormasamir.\n3. Úrkoma: Vetrarúrkoma á Íslandi er yfirleitt mikil, sérstaklega í formi rigningar eða snjókoma.\n4. Snjór: Snjór er algengur á Íslandi á veturna, sérstaklega í fjöllum og á hálendi.\n5. Skammdegi: Á veturna er dagurinn stuttur á Íslandi, sérstaklega í desember og janúar þegar sólin rís ekki fyrr en um 10:30 og setur um 15:30.\n6. Stormar: Vetrarstormar á Íslandi geta verið miklir og valdið erfiðleikum í samgöngum og annarri starfsemi.\n\nÍ heildina er veðrið á Íslandi á veturna kalt, óstöðugt og getur verið miklu óvænt. Það er mikilvægt að vera vel undirbúinn og hafa rétta klæðnað og búnað til að takast á við vetrarveðrið á Íslandi."},
        {"role": "user", "content": "Hvernig er veðrið á sumrin?"}
    ]
    references = [
        "Meðalhiti á Íslandi á sumrin er um 10-15°C.",
        "Sumarið á Íslandi einkennist af löngum björtum dögum vegna miðnætursólarinnar."
    ]

    response = generate_llm_response(chat_history, references)
    print(response)
