# pdf_tool.py (fragmento relevante)
import os
import uuid
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfObject
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from datetime import datetime, timedelta

def fill_pdf(
    datos: dict,
    input_pdf: str = "Heirs+Determination+Worksheet+rev+5-2022+Fillable.pdf",
    output_basename: str = "Heirs_Determination_Filled"
) -> str:
    """
    Rellena el PDF, lo sube con un nombre UUID, y devuelve una URL con SAS de 1h.
    """
    # 1) Generar nombre único
    unique_id   = uuid.uuid4()
    blob_name   = f"{unique_id}.pdf"                             # solo UUID.pdf
    # o bien: blob_name = f"{unique_id}_{output_basename}.pdf"    # UUID_[basename].pdf

    local_path  = f"{output_basename}.pdf"

    # 2) Llenar el PDF (igual que antes)
    pdf = PdfReader(input_pdf)
    for page in pdf.pages:
        if page.Annots:
            for ann in page.Annots:
                if ann.Subtype == "/Widget" and ann.T:
                    key = ann.T[1:-1]
                    if key in datos:
                        key = ann.T[1:-1]
                        value = datos.get(key)

                        # Si no hay valor (None o cadena vacía), no escribimos nada
                        if value is None or (isinstance(value, str) and not value.strip()):
                            continue

                        # Sólo escribimos si value NO es None/""
                        ann.V = PdfObject(f'({value})')
                        ann.AP = PdfDict()
    pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))
    PdfWriter(local_path, trailer=pdf).write()

    # 3) Subir al contenedor con el nombre UUID
    conn_str     = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container    = os.getenv("BLOB_CONTAINER_NAME")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    blob_client  = blob_service.get_blob_client(container=container, blob=blob_name)
    with open(local_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=True)

    # 4) Generar SAS token
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key  = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    sas_token    = generate_blob_sas(
        account_name=account_name,
        account_key=account_key,
        container_name=container,
        blob_name=blob_name,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    return f"{blob_client.url}?{sas_token}"
