import typing
import streamlit as st
from uuid import uuid4
from streamlit.delta_generator import DeltaGenerator
from datetime import date
from typing import Any
from pydantic import BaseModel, HttpUrl
from pydantic.fields import FieldInfo


def unwrap_optional(annotation):
    args = typing.get_args(annotation)
    non_none = [a for a in args if a is not type(None)]
    return non_none[0] if non_none else annotation

def render_field(container: DeltaGenerator, name: str, info: FieldInfo, value: Any) -> Any:
    
    mapped_input_func = {
        str: container.text_input,
        date: container.date_input,
        int: container.number_input,
        HttpUrl: container.text_input,
        'textarea': container.text_area
    }
    # first check for the extra json schema 

    typewidget = info.json_schema_extra.get('widget') if info.json_schema_extra else unwrap_optional(info.annotation)

    return mapped_input_func[typewidget](label=info.title, value=value)



def generic_form(form_data_model: type[BaseModel], input_model: BaseModel | None = None) -> BaseModel:

    form_data = form_data_model()

    form_container = st.container(key=f"{form_data_model.__name__}-{uuid4()}", border=True)
    form_container.subheader(form_data_model.__name__)

    for name, info in form_data.__class__.model_fields.items():

        existing = getattr(input_model, name, None) if input_model else None

        if type(existing) == HttpUrl:
            existing = str(existing)

        setattr(form_data, name, render_field(form_container, name, info, existing))

    return form_data 

        






