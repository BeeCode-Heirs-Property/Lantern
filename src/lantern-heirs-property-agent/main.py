import os
import json
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from openai import AzureOpenAI  # Asegúrate de que tu paquete openai esté configurado para Azure OpenAI
from models import WorksheetResponse, ChatMessage, OriginalOwnerWorksheet
from pdf_tool import fill_pdf

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Definición de la función herramienta que usará el LLM
functions = [
    {
        "name": "fill_pdf",
        "description": "Generate the final PDF of the Heirs Determination Worksheet form using form_data.",
        "parameters": {
            "type": "object",
            "properties": {
                "form_data": OriginalOwnerWorksheet.schema()
            },
            "required": ["form_data"]
        },
    }
]

key_mapping = {
    'name_of_original_owner': 'Name of Original Owner',
    'date_of_death': 'Date of Death',
    'county_state_of_death': 'County State of Death',
    'did_they_have_a_will': 'Did they have a Will',
    'was_estate_probated': 'was_estate_probated_owner',
    'estate_administrator_or_executor': 'If their estate was probated who is the administrator or executor',
    'were_they_married_when_they_passed': 'were_they_married_when_they_passed',
    'spouses_name': 'Spouses Name',
    'spouse_had_children_not_of_original_owner': 'spouse_had_children_not_of_original_owner',
    'spouse_remarried': 'spouse_remarried',
    'subsequent_spouse_name': 'If Yes Name of Subsequent Spouse',
    'spouse_date_of_death': 'Spouses Date of Death',
    'spouse_county_state_of_death': 'County State of Death_2',
    'spouse_had_will': 'spouse_had_will',
    'spouse_estate_probated': 'spouse_estate_probated',
    'spouse_estate_administrator_or_executor': 'If their estate was probated who is the administrator or the executor',
    'mother_name': 'What was their mothers name',
    'mother_date_of_death': 'Date of Death_2',
    'father_name': 'What was their fathers name',
    'father_date_of_death': 'Date of Death_3'
}

def validate_dict(form_dict):
    return all(value and str(value).strip() for value in form_dict.values())

# Configurar archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# ruteo de páginas
@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    """Página de inicio con información de la organización ficticia"""
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def read_chat(request: Request):
    """Página de chat para asistencia y llenado de formularios"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Mensaje de bienvenida al conectarse
    welcome_message = {
        "message": (
            "Welcome to specialized Heirs’ Property support for Georgia. 🏘️"
            "\nI’m here to answer your questions about the process and guide you through filling out the forms. "
            "<ul><li>At the moment, we have the following form available:</li></ul>"
            "<ul><li>- 'HEIRS DETERMINATION WORKSHEETS FOR THE STATE OF GEORGIA (Original Owner Worksheet)'</li></ul>"
        ),
        "form_data": {},
        "field_updated": None,
        "form_completed": False
    }
    await websocket.send_json(welcome_message)

    while True:
        try:
            raw = await websocket.receive_text()
            message: dict = json.loads(raw)

            # Imprime lo recibido para debugging
            print(">>> Mensaje recibido:", message)

            current_form = message.get("current_form", {})
            print(">>> Estado actual del formulario recibido:", current_form)

            # Se construye el mensaje para el LLM

            system_message = (
                "You are a helpful AI assistant completing the Original Owner Worksheet of the Georgia Heirs Determination form. "
                "Your responses should be natural and conversational. Your language should always be english."
                f"Current form state: {json.dumps(current_form)}\n\n"
                "When you receive new information, update the `form_data` field with the updated values "
                "and return a confirmation message. Ask follow-up questions for any missing required fields. "
                "If you update a field, set `field_updated` to the snake_case name of that field.\n\n"                
                "When all the fields are filled in the form (current form), you should invoke the function fill_pdf and pass current_form as arguments "
                "Example response structure:\n"
                "- message: 'Great, I've recorded the original owner's name. What's the date of death?'\n"
                "- form_data: {updated form data}\n"
                "- field_updated: 'name_of_original_owner'"
            )

            user_content = message["content"]
            last_question = message["last_question"]

            print(">>> Contenido completo enviado al LLM:")
            print(json.dumps([
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content}
            ], indent=2))

            completion = client.beta.chat.completions.parse(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f'last_question: {last_question}, user_answer: {user_content}'},
                ],
                functions=functions,
                #function_call="auto",
                response_format=WorksheetResponse,
            )

            choice = completion.choices[0]

            # ¿El LLM solicitó la función?
            if choice.message.function_call and choice.message.function_call.name == "fill_pdf":
                print(">>> El modelo invocó la función fill_pdf")
                args = json.loads(choice.message.function_call.arguments)
                preform_data = args.get("form_data", {})

                # 1) Extraer nombre y contacto para después la API
                applicant_name = preform_data.get("applicant_name")
                applicant_contact = preform_data.get("applicant_contact")

                print(f'form_data:{preform_data}')

                pdf_fields = {
                    key_mapping[k]: v
                    for k, v in preform_data.items()
                    if k in key_mapping and v is not None and str(v).strip()
                }

                # ✅ Verificación estricta: ambos campos deben existir Y tener contenido no vacío
                if not pdf_fields.get('Name of Original Owner') or not pdf_fields.get("Date of Death"):
                    print("❌ El modelo intentó generar PDF sin tener ambos campos válidos.")
                    await websocket.send_json({
                        "message": "Aún no tengo toda la información para generar el PDF. ¿Podrías darme los datos que faltan?",
                        "error": True
                    })
                    continue

                # Todo OK, generamos el PDF
                pdf_url = fill_pdf(pdf_fields)
                base_blob_url = pdf_url.split("?", 1)[0]

                # Llamar API para registrar en base de datos
                async with httpx.AsyncClient() as client_api:
                    await client_api.post(
                        "https://beecode-api.azurewebsites.net/api/records",
                        json={
                            "userName": applicant_name,
                            "phoneNumber": applicant_contact,
                            "link": base_blob_url
                        }
                    )

                await websocket.send_json({"pdf_url": pdf_url})
                continue

            # ...
            # Si no hay llamada a función, es una respuesta normal
            resp = completion.choices[0].message.parsed
            if not isinstance(resp, dict):
                resp = resp.dict()

            print(">>> Respuesta del LLM:", resp)

            # Actualizar el current_form usando los datos recibidos del LLM

            if resp.get("form_data"):
                # Aquí se actualiza el estado en el servidor para enviarlo al cliente
                #current_form = resp["form_data"]
                # 1. Ver qué está tratando de actualizar el LLM
                print(">>> Datos recibidos para fusionar:", resp["form_data"])
                # 2. Fusiona sin borrar lo anterior
                current_form.update(resp["form_data"])
                print(">>> ✅ Formulario tras update():", current_form)
                #print(f"form_data {form_data}")

            # Enviar la respuesta junto con el estado actualizado del formulario
            await websocket.send_json({
                "message": resp.get("message", ""),
                "form_data": current_form,
                "field_updated": resp.get("field_updated")
            })


        except Exception as e:
            print(e)
            await websocket.send_json({
                "message": "Lo siento, no pude procesar esa petición. ¿Puedes intentar de nuevo?",
                "error": True
            })


@app.post("/fill_pdf")
async def generate_pdf(form_data: dict = Body(...)):
    from pdf_tool import fill_pdf
    try:
        pdf_url = fill_pdf(form_data)
        return {"pdf_url": pdf_url}
    except ValueError as e:
        return {"error": True, "messages": str(e).split("\n")}

'''
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
'''

@app.on_event("startup")
async def startup_event():
    print("🚀 FastAPI arrancado y listo para rellenar el formulario Heirs' Property")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)