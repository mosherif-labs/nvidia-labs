import base64, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # nearest .env, searching up from this file

nim = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
VLM = os.environ.get("VLM_MODEL", "meta/llama-3.2-11b-vision-instruct")
PROMPT = (
    "Extract from this bank statement as JSON only: account_holder, account_number, iban, period, "
    "transactions (list of {date, description, amount}). Copy values exactly as printed."
)


def read_document(image_path: str) -> str:
    b64 = base64.b64encode(open(image_path, "rb").read()).decode()
    r = nim.chat.completions.create(
        model=VLM,
        max_tokens=1024,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
    )
    return r.choices[0].message.content
