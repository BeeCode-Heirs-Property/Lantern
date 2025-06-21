# models.py

from pydantic import BaseModel, Field
from typing import Optional

class OriginalOwnerWorksheet(BaseModel):
    applicant_name: str = Field(
        ...,
        description="Full name of the person requesting the form"
    )
    applicant_contact: str = Field(
        ...,
        description="Contact number of the person requesting the form"
    )
    name_of_original_owner: str = Field(
        ...,
        description="Name of Original Owner"
    )
    date_of_death: str = Field(
        ...,
        description="Date of Death (e.g., MM/DD/YYYY)"
    )

    #'''
    county_state_of_death: str = Field(
        ..., description="County, State of Death"
    )
    did_they_have_a_will: str = Field(
        ..., description="Did they have a Will? Options: Yes, No, Unknown"
    )

    was_estate_probated: str = Field(
        ..., description="Was their estate probated? Options: Yes, No, Unknown"
    )
    estate_administrator_or_executor: Optional[str] = Field(
        None,
        description="Administrator or executor if the original owner's estate was probated",
    )
    were_they_married_when_they_passed: str = Field(
        ..., description="Were they married when they passed? Options: Yes, No"
    )
    spouses_name: Optional[str] = Field(
        None, description="Spouse's name if married"
    )
    spouse_had_children_not_of_original_owner: str = Field(
        ...,
        description="Did their spouse have children not of the original owner? Options: Yes, No",
    )
    spouse_remarried: str = Field(
        ..., description="Did their spouse remarry? Options: Yes, No"
    )
    subsequent_spouse_name: Optional[str] = Field(
        None, description="Name of subsequent spouse if remarried"
    )
    spouse_date_of_death: Optional[str] = Field(
        None, description="Date of death of subsequent spouse"
    )
    spouse_county_state_of_death: Optional[str] = Field(
        None, description="County, State of death of subsequent spouse"
    )
    spouse_had_will: Optional[str] = Field(
        None, description="Did their spouse have a Will? Options: Yes, No, Unknown"
    )
    spouse_estate_probated: Optional[str] = Field(
        None, description="Was their spouse's estate probated? Options: Yes, No, Unknown"
    )
    spouse_estate_administrator_or_executor: Optional[str] = Field(
        None,
        description="Administrator or executor for the spouse's estate if probated",
    )
    mother_name: Optional[str] = Field(
        None, description="Original owner's mother's name"
    )
    mother_date_of_death: Optional[str] = Field(
        None, description="Mother's date of death"
    )
    father_name: Optional[str] = Field(
        None, description="Original owner's father's name"
    )
    father_date_of_death: Optional[str] = Field(
        None, description="Father's date of death"
    )
    #'''

class WorksheetResponse(BaseModel):
    message: str = Field(..., description="Assistant's response message")
    form_data: Optional[OriginalOwnerWorksheet] = Field(
        None, description="Updated form data"
    )
    field_updated: Optional[str] = Field(
        None, description="Name of the field that was just updated"
    )
    form_completed: bool  = Field(..., description="True if the all fields are filled")


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    content: str = Field(..., description="Message content")
