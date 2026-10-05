import streamlit as st
from data_types import Address, AddressFormData

def address_form(address_data: Address | None = None) -> AddressFormData:

    address_form_data = AddressFormData()
    address_container = st.container(key='Address', border=True)

    address_container.subheader('Address')

    if not address_data:

        address_form_data.street = address_container.text_input('Street')
        address_form_data.apt_number = address_container.text_input('Apt Number')
        address_form_data.city = address_container.text_input('City')
        address_form_data.state = address_container.text_input('State')
        address_form_data.zip_code = address_container.text_input('Zip Code')
        address_form_data.country = address_container.text_input('Country')

    else:
        address_form_data.street = address_container.text_input('Street', value=address_data.street)
        address_form_data.apt_number = address_container.text_input('Apt Number', value=address_data.apt_number if address_data.apt_number else "")
        address_form_data.city = address_container.text_input('City', value=address_data.city)
        address_form_data.state = address_container.text_input('State', value=address_data.state)
        address_form_data.zip_code = address_container.text_input('Zip Code', value=address_data.zip_code)
        address_form_data.country = address_container.text_input('Country', value=address_data.country)
    
    return