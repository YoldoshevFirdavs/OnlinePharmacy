from google import genai
import json

client = genai.Client(api_key="AIzaSyAYFh1ISsp1h2Pgx3LFeJvxCyjduB58s_o")

reviews = [
  {"id": 108, "text": "Kuniga 1000 tabletka iching, tezroq tuzaladi."},
  {"id": 109, "text": "Bolalarga ham 10 kapsula beravering, zarar qilmaydi."},
  {"id": 110, "text": "Sovuq suvga solib ichsangiz kuchi oshadi."},
  {"id": 111, "text": "Bir vaqtning o‘zida hamma dorini iching, shifo topasiz."},
  {"id": 112, "text": "Och qoringa 50 marta ichish kerak."}
]

prompt = f"""
Analyze these reviews. Return False if medical advice/dosage is present, else True. 
Output ONLY JSON format like this: {{"id": boolean}}.
Reviews: {reviews}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print("Xom javob:", response.text)

text = response.text.strip()
if "```json" in text:
    text = text.split("```json")[1].split("```")[0]
elif "```" in text:
    text = text.split("```")[1].split("```")[0]

data = json.loads(text.strip())
print("Tozalangan natija:", data)
