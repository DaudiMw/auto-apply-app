import enum
import types
import typing
from datetime import date
from typing import Any, get_args, get_origin
import streamlit as st
from pydantic import BaseModel, HttpUrl
from pydantic.fields import FieldInfo
from streamlit.delta_generator import DeltaGenerator


def unwrap_type(annotation: Any) -> Any:
    """Unwraps Annotated, Union, and Optional types to get the underlying concrete type."""
    if annotation is None:
        return str

    # Unwrap Annotated[T, ...]
    origin = get_origin(annotation)
    if origin is typing.Annotated:
        args = get_args(annotation)
        if args:
            annotation = args[0]
            origin = get_origin(annotation)

    # Unwrap Union[T, None] / Optional[T] / T | None
    if origin in (typing.Union, types.UnionType):
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return unwrap_type(non_none[0])
        return str

    return annotation


def render_field(
    container: DeltaGenerator,
    name: str,
    info: FieldInfo,
    value: Any,
    field_key: str,
) -> Any:
    """Renders the appropriate Streamlit widget for a Pydantic model field."""
    label = info.title or name.replace("_", " ").title()
    widget_override = (
        info.json_schema_extra.get("widget") if info.json_schema_extra else None
    )
    unwrapped = unwrap_type(info.annotation)

    # 1. Custom widget overrides
    if widget_override == "textarea":
        str_val = str(value) if value is not None else ""
        return container.text_area(label=label, value=str_val, key=field_key)

    # 2. Enum / StrEnum -> selectbox
    if isinstance(unwrapped, type) and issubclass(unwrapped, enum.Enum):
        options = [e.value for e in unwrapped]
        idx = 0
        if value is not None:
            val_str = value.value if isinstance(value, enum.Enum) else str(value)
            if val_str in options:
                idx = options.index(val_str)
        return container.selectbox(label=label, options=options, index=idx, key=field_key)

    # 3. Boolean -> checkbox
    if unwrapped is bool:
        bool_val = bool(value) if value is not None else False
        return container.checkbox(label=label, value=bool_val, key=field_key)

    # 4. Date -> date_input
    if unwrapped is date:
        date_val = value if isinstance(value, date) else None
        return container.date_input(
            label=label,
            value=date_val,
            min_value=date(1950, 1, 1),
            max_value=date(2040, 1, 1),
            key=field_key,
        )

    # 5. Integer / Number -> number_input
    if unwrapped in (int, float) or (isinstance(unwrapped, type) and issubclass(unwrapped, int)):
        num_val = int(value) if value is not None else 0
        return container.number_input(label=label, value=num_val, step=1, key=field_key)

    # 6. List of strings -> text_input comma-separated
    if unwrapped is list or get_origin(unwrapped) is list:
        if isinstance(value, list):
            list_str = ", ".join(str(item) for item in value)
        else:
            list_str = str(value) if value is not None else ""
        raw_result = container.text_input(
            label=f"{label} (comma-separated)",
            value=list_str,
            key=field_key,
        )
        return [item.strip() for item in raw_result.split(",") if item.strip()]

    # 7. Default to text_input for str, HttpUrl, PhoneNumber, EmailStr, etc.
    str_val = str(value) if value is not None else ""
    return container.text_input(label=label, value=str_val, key=field_key)


def generic_form(
    form_data_model: type[BaseModel],
    input_model: BaseModel | None = None,
    key_prefix: str = "generic_form",
    title: str | None = None,
    border: bool = True,
) -> BaseModel:
    """Renders a Pydantic model into Streamlit input widgets and returns the instantiated model."""
    container_title = title or form_data_model.__name__.replace("FormData", "").replace("Model", "")
    form_container = st.container(key=f"container_{key_prefix}", border=border)

    if container_title:
        form_container.subheader(container_title)

    collected_data: dict[str, Any] = {}

    for name, info in form_data_model.model_fields.items():
        existing_val = getattr(input_model, name, None) if input_model else None

        if isinstance(existing_val, HttpUrl):
            existing_val = str(existing_val)

        field_key = f"{key_prefix}_{name}"
        field_val = render_field(form_container, name, info, existing_val, field_key)

        # Sanitize empty string values for non-string / optional types (e.g. HttpUrl, numbers, dates)
        unwrapped = unwrap_type(info.annotation)
        if field_val == "" and unwrapped is not str:
            field_val = None

        collected_data[name] = field_val

    # Construct and return the form data model instance
    return form_data_model(**collected_data)


def dynamic_list_form(
    item_model: type[BaseModel],
    current_items: list[BaseModel] | None = None,
    key_prefix: str = "list_form",
    item_title: str = "Entry",
) -> list[BaseModel]:
    """Renders a dynamic list of Pydantic model forms with add/remove controls."""
    state_key = f"{key_prefix}_count"
    current_items = current_items or []

    if state_key not in st.session_state:
        st.session_state[state_key] = max(len(current_items), 1)

    count = st.session_state[state_key]
    items: list[BaseModel] = []

    for i in range(count):
        existing = current_items[i] if i < len(current_items) else None
        item_prefix = f"{key_prefix}_{i}"

        with st.container(border=True):
            cols = st.columns([0.85, 0.15])
            with cols[0]:
                st.markdown(f"**{item_title} #{i + 1}**")
            with cols[1]:
                if count > 0 and st.button(":material/delete:", key=f"remove_{item_prefix}", help=f"Remove {item_title} #{i + 1}"):
                    st.session_state[state_key] = max(0, count - 1)
                    st.rerun()

            entry = generic_form(
                form_data_model=item_model,
                input_model=existing,
                key_prefix=item_prefix,
                title="",
                border=False,
            )
            items.append(entry)

    if st.button(f":material/add: Add {item_title}", key=f"add_{key_prefix}"):
        st.session_state[state_key] = count + 1
        st.rerun()

    return items
