import streamlit as st
import qrcode
import io
import base64
import json
import re
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Truck QR Generator", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS personalizado para estilos específicos ---
st.markdown("""
<style>
/* Oculta la cabecera por defecto de Streamlit si no la necesitas */
.stApp > header {
    display: none;
}
.st-emotion-cache-z5fcl4 { 
    padding-top: 2rem;
}

/* Responsive design */
@media (max-width: 768px) {
    .st-emotion-cache-msvmlr h1 {
        font-size: 28px !important;
    }
    .form-container {
        padding: 20px !important;
        margin: 20px auto !important;
    }
    .stButton button {
        font-size: 16px !important;
    }
}

@media (max-width: 480px) {
    .st-emotion-cache-msvmlr h1 {
        font-size: 24px !important;
    }
    .form-container {
        padding: 15px !important;
        margin: 15px auto !important;
    }
}
            
/* ----------------------------------------------- */
/* Estilos para el TÍTULO (h1) */
/* ----------------------------------------------- */
.st-emotion-cache-msvmlr h1 {
    text-align: center;
    color: #262730; /* Asegura el color del título en negro */
    font-size: 36px; /* ¡NUEVO! Cambia el tamaño de la fuente del título (ejemplo: 48px) */
    padding-top: 5px; /* ¡NUEVO! Reduce el padding superior del título para ajustar el margen */
    margin-top: 0; /* Mantiene el margen superior en 0 */
    #font-family: 'Helvetica', sans-serif; 
    font-weight: 800; /* Hace el título más negrita si la fuente lo permite */
}

/* ----------------------------------------------- */
/* Estilo para el contenedor principal de la aplicación (el fondo blanco ya viene de config.toml) */
/* ----------------------------------------------- */
.stApp {
    font-family: 'Roboto', sans-serif; /* ¡NUEVO! Cambia la tipografía de toda la aplicación */
}

/* ----------------------------------------------- */
/* Estilo para el contenedor del formulario */
/* ----------------------------------------------- */
.form-container {
    background-color: #F5F5F5; /* Fondo gris claro para el formulario */
    padding: 30px; /* Espacio interno dentro del rectángulo */
    border-radius: 0px; /* Bordes NO redondeados */
    margin: 40px auto; /* Centra el rectángulo horizontalmente y le da margen vertical */
    max-width: 700px; /* Ancho máximo del rectángulo del formulario */
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* Sutil sombra para destacarlo */
}

/* Quitar bordes redondeados a los campos de entrada y selectores dentro del formulario */
.st-emotion-cache-1f1iymw, /* Contenedor principal del formulario si se usa st.form */
.st-emotion_cache-j7qwjs, /* Clases de Streamlit para text_input */
.st-emotion-cache-l9bilg, /* Clase para date_input */
.st-emotion-cache-1wivd2v, /* Clase para selectbox (fondo) */
.st-emotion-cache-1v0bbxx, /* Clase para text_area */
.st-emotion-cache-16t8w3t, /* Otra clase de contenedores/widgets */
.st-emotion-cache-e1y0t1k { /* Una clase común para muchos widgets de entrada */
    border-radius: 0px !important; /* Forzar bordes cuadrados */
}

/* ----------------------------------------------- */
/* Ajusta el ancho y estilo del botón, incluyendo el tamaño de fuente y el efecto hover */
/* ----------------------------------------------- */
.stButton button {
    width: 100%; /* El botón ocupa todo el ancho disponible en su columna */
    border-radius: 0px !important; /* Quita el redondeado del botón */
    border: 1px solid #4CAF50; /* Borde sólido del mismo color que el fondo */
    color: white !important; /* Texto del botón en blanco */
    background-color: #4CAF50 !important; /* Fondo del botón verde */
    font-size: 18px !important; /* Aumenta el tamaño de la fuente del botón */
    transition: background-color 0.2s ease; /* Suaviza la transición de color al pasar el ratón */
}

/* Efecto hover: cambia el color de fondo cuando el ratón está encima */
.stButton button:hover {
    background-color: #45a049 !important; /* Un verde un poco más oscuro al pasar el ratón */
    border-color: #45a049 !important; /* Cambia también el borde para que coincida */
}

/* Mensajes de error */
.st-emotion-cache-hkp202 p { /* Clase para el texto de los errores */
    color: #D32F2F; /* Color rojo para el texto de los errores */
}

/* Centrar QR code */
.qr-container {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 20px 0;
}

/* Estilo para mensajes de éxito */
.success-message {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 10px;
    border-radius: 4px;
    margin: 10px 0;
}

/* Estilo para mensajes de advertencia */
.warning-message {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    color: #856404;
    padding: 10px;
    border-radius: 4px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass

class TruckQRGenerator:
    """Clase principal para generar códigos QR de tracking de camiones"""
    
    # Patrones de validación
    PLATE_PATTERN = re.compile(r'^[A-Z0-9-]{3,10}$')
    CUSTOMER_ID_PATTERN = re.compile(r'^[A-Z0-9_-]{3,20}$')
    DELIVERY_REF_PATTERN = re.compile(r'^[A-Z0-9_-]{3,30}$')
    ITEM_ID_PATTERN = re.compile(r'^[A-Z0-9_-]{1,20}$')
    
    # Configuración para Boomi
    BOOMI_CONFIG = {
        'date_format': '%Y-%m-%dT%H:%M:%S',  # Formato ISO para Boomi
        'required_fields': ['plate', 'driverName', 'customer_id', 'date_time_at_gate', 'item_list'],
        'truck_types': ['Type A', 'Type B', 'Type C', 'Type D', 'Type E']
    }
    
    @staticmethod
    def validate_plate(plate: str) -> bool:
        """Valida el formato de la placa"""
        if not plate or len(plate.strip()) < 3:
            return False
        return bool(TruckQRGenerator.PLATE_PATTERN.match(plate.strip().upper()))
    
    @staticmethod
    def validate_driver_name(driver: str) -> bool:
        """Valida el nombre del conductor"""
        if not driver or len(driver.strip()) < 2:
            return False
        # Solo letras, espacios y algunos caracteres especiales
        return bool(re.match(r'^[A-Za-z\s\.\-\']{2,50}$', driver.strip()))
    
    @staticmethod
    def validate_customer_id(customer_id: str) -> bool:
        """Valida el ID del cliente"""
        if not customer_id or len(customer_id.strip()) < 3:
            return False
        return bool(TruckQRGenerator.CUSTOMER_ID_PATTERN.match(customer_id.strip().upper()))
    
    @staticmethod
    def validate_delivery_ref(delivery_ref: str) -> bool:
        """Valida la referencia de entrega"""
        if not delivery_ref:
            return True  # Campo opcional
        return bool(TruckQRGenerator.DELIVERY_REF_PATTERN.match(delivery_ref.strip().upper()))
    
    @staticmethod
    def validate_company(company: str) -> bool:
        """Valida el nombre de la empresa"""
        if not company:
            return True  # Campo opcional
        return len(company.strip()) >= 2 and len(company.strip()) <= 100
    
    @staticmethod
    def validate_items(items_raw: str) -> Tuple[bool, List[Dict], List[str]]:
        """Valida y procesa la lista de items"""
        errors = []
        item_list = []
        
        if not items_raw or not items_raw.strip():
            return False, [], ["The 'Items' field is required."]
        
        # Procesar items
        raw_items = [item.strip() for item in items_raw.split(',') if item.strip()]
        
        if not raw_items:
            return False, [], ["The 'Items' field is required and does not contain valid items."]
        
        seen_items = set()
        
        for item_entry in raw_items:
            parts = item_entry.split(':')
            if len(parts) != 2:
                errors.append(f"Invalid item format: '{item_entry}'. Use 'SKU:Quantity'.")
                continue
            
            item_id = parts[0].strip().upper()
            quantity_str = parts[1].strip()
            
            # Validar ID del item
            if not TruckQRGenerator.ITEM_ID_PATTERN.match(item_id):
                errors.append(f"Invalid item ID format: '{item_id}'. Use only letters, numbers, hyphens and underscores.")
                continue
            
            # Validar duplicados
            if item_id in seen_items:
                errors.append(f"Duplicate item ID: '{item_id}'.")
                continue
            
            seen_items.add(item_id)
            
            # Validar cantidad
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    errors.append(f"Quantity for '{item_id}' must be a positive number.")
                    continue
                
                item_list.append({"item_id": item_id, "quantity": quantity})
            except ValueError:
                errors.append(f"Quantity '{quantity_str}' for '{item_id}' is not a valid number.")
        
        return len(errors) == 0, item_list, errors
    
    @staticmethod
    def validate_datetime(selected_date, selected_hour: str, selected_minute: str, selected_ampm: str) -> Tuple[bool, Optional[str], List[str]]:
        """Valida y procesa la fecha y hora"""
        errors = []
        
        if not selected_date:
            errors.append("The 'Date' field is required.")
        
        if not selected_hour or not selected_minute:
            errors.append("The 'Hours' and 'Minutes' fields are required.")
        
        if errors:
            return False, None, errors
        
        try:
            h_12 = int(selected_hour)
            m = int(selected_minute)
            
            # Convertir a formato 24 horas
            if selected_ampm == "PM" and h_12 != 12:
                h_24 = h_12 + 12
            elif selected_ampm == "AM" and h_12 == 12:
                h_24 = 0
            else:
                h_24 = h_12
            
            if not (0 <= h_24 <= 23 and 0 <= m <= 59):
                errors.append("Invalid time format.")
                return False, None, errors
            
            # Crear datetime y validar que no sea en el futuro
            combined_datetime = datetime(selected_date.year, selected_date.month, selected_date.day, h_24, m)
            
            if combined_datetime > datetime.now():
                errors.append("Date and time cannot be in the future.")
                return False, None, errors
            
            # Formato ISO para Boomi
            dt_iso = combined_datetime.strftime(TruckQRGenerator.BOOMI_CONFIG['date_format'])
            
            return True, dt_iso, []
            
        except ValueError as e:
            errors.append(f"Error processing time: {str(e)}")
            return False, None, errors
    
    @staticmethod
    def generate_qr_optimized(data_dict: Dict) -> Tuple[str, str]:
        """Genera un código QR optimizado para Boomi"""
        
        # Limpiar datos nulos o vacíos para optimizar tamaño
        cleaned_data = {k: v for k, v in data_dict.items() if v is not None and v != ""}
        
        # Generar JSON con formato legible
        json_str = json.dumps(cleaned_data, indent=2, ensure_ascii=False)
        
        # Generar QR con configuración optimizada
        qr = qrcode.QRCode(
            version=None,  # Auto-determinar versión
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Mejor balance entre corrección y tamaño
            box_size=8,  # Tamaño óptimo para lectura
            border=4
        )
        
        qr.add_data(json_str)
        qr.make(fit=True)
        
        # Crear imagen con alta calidad
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        base64_qr = base64.b64encode(buf.getvalue()).decode()
        
        return base64_qr, json_str

# Inicializar el generador
generator = TruckQRGenerator()

# Título de la aplicación visible al usuario
st.title("TRUCK TRACKING QR GENERATOR") 

# --- Inicializar estado de la sesión ---
if "form_active" not in st.session_state:
    st.session_state.form_active = True
if "qr_base64" not in st.session_state:
    st.session_state.qr_base64 = ""
if "json_str" not in st.session_state:
    st.session_state.json_str = ""
if "selected_date_value" not in st.session_state:
    st.session_state.selected_date_value = datetime.now().date()
if "selected_hour_value" not in st.session_state:
    st.session_state.selected_hour_value = datetime.now().strftime("%I")
if "selected_minute_value" not in st.session_state:
    st.session_state.selected_minute_value = datetime.now().strftime("%M")
if "ampm_selection_index" not in st.session_state:
    st.session_state.ampm_selection_index = 0 if datetime.now().hour < 12 else 1

def return_to_form():
    """Vuelve al formulario principal"""
    st.session_state.form_active = True
    st.session_state.qr_base64 = ""
    st.session_state.json_str = ""
    st.session_state.selected_date_value = datetime.now().date()
    st.session_state.selected_hour_value = datetime.now().strftime("%I")
    st.session_state.selected_minute_value = datetime.now().strftime("%M")
    st.session_state.ampm_selection_index = 0 if datetime.now().hour < 12 else 1


def generate_qr_and_update_state(data_dict: Dict):
    """Genera el QR y actualiza el estado"""
    try:
        base64_qr, json_str = generator.generate_qr_optimized(data_dict)
        st.session_state.qr_base64 = base64_qr
        st.session_state.json_str = json_str
        st.session_state.form_active = False
        st.rerun()
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

# --- Lógica condicional para mostrar el formulario o el resultado del QR ---
if st.session_state.form_active:
    st.markdown("Fill in the details to generate a QR code.")

    # Campos principales
    col_plate, col_driver = st.columns(2)
    with col_plate:
        plate = st.text_input(
            "Plate number (required)",
            key="plate_input",
            placeholder="e.g., ABC-123",
            help="3-10 characters, letters, numbers, and hyphens only"
        )
    with col_driver:
        driver = st.text_input(
            "Driver name (required)",
            key="driver_input",
            placeholder="e.g., John Doe",
            help="2-50 characters, letters and spaces only"
        )
        
    customer_id = st.text_input(
        "Customer ID (required)",
        key="customer_id_input",
        placeholder="e.g., CUST001",
        help="3-20 characters, letters, numbers, hyphens, and underscores only"
    )

    # Campos de fecha y hora
    col_date, col_hour, col_minute, col_ampm = st.columns([1, 0.25, 0.25, 0.5])

    with col_date:
        selected_date = st.date_input(
            "Date",
            value=st.session_state.selected_date_value,
            format="DD/MM/YYYY",
            key="date_input",
            max_value=datetime.now().date(),
            help="Cannot be in the future"
        )
        st.session_state.selected_date_value = selected_date

    with col_hour:
        hour_options = [f"{i:02d}" for i in range(1, 13)]
        default_hour_index = hour_options.index(st.session_state.selected_hour_value) if st.session_state.selected_hour_value in hour_options else 0
        selected_hour = st.selectbox(
            "Hours",
            options=hour_options,
            index=default_hour_index,
            key="hour_selectbox"
        )
        st.session_state.selected_hour_value = selected_hour

    with col_minute:
        minute_options = [f"{i:02d}" for i in range(0, 60)]
        default_minute_index = minute_options.index(st.session_state.selected_minute_value) if st.session_state.selected_minute_value in minute_options else 0
        selected_minute = st.selectbox(
            "Minutes",
            options=minute_options,
            index=default_minute_index,
            key="minute_selectbox"
        )
        st.session_state.selected_minute_value = selected_minute

    with col_ampm:
        ampm_options = ["AM", "PM"]
        selected_ampm = st.selectbox(
            "AM/PM",
            options=ampm_options,
            index=st.session_state.ampm_selection_index,
            key="ampm_selectbox"
        )
        st.session_state.ampm_selection_index = ampm_options.index(selected_ampm)

    # Campos opcionales
    truck_type = st.selectbox(
        "Truck type", 
        options=[""] + generator.BOOMI_CONFIG['truck_types'], 
        key="truck_type_input",
        help="Select truck type from predefined options"
    )

    company = st.text_input(
        "Company",
        key="company_input",
        placeholder="e.g., Logistics Inc.",
        help="2-100 characters, optional field"
    )
    
    delivery_ref = st.text_input(
        "Delivery Order Reference",
        key="delivery_ref_input",
        placeholder="e.g., DO-2024-001",
        help="3-30 characters, letters, numbers, hyphens, and underscores only"
    )

    items_raw = st.text_area(
        "Items (required, format: SKU:Quantity)",
        key="items_input",
        placeholder="e.g., ITEM001:10, ITEM002:5",
        help="Format: SKU:Quantity separated by commas"
    )

    # Botón para generar QR
    col_left_btn, col_center_btn, col_right_btn = st.columns([1, 2, 1])
    with col_center_btn:
        if st.button("Generate QR"):
            errors = []
            
            # Validaciones
            if not generator.validate_plate(plate):
                errors.append("Invalid plate number format. Use 3-10 characters with letters, numbers, and hyphens only.")
            
            if not generator.validate_driver_name(driver):
                errors.append("Invalid driver name. Use 2-50 characters with letters, spaces, dots, hyphens, and apostrophes only.")
            
            if not generator.validate_customer_id(customer_id):
                errors.append("Invalid customer ID format. Use 3-20 characters with letters, numbers, hyphens, and underscores only.")
            
            if not generator.validate_company(company):
                errors.append("Company name must be between 2 and 100 characters.")
            
            if not generator.validate_delivery_ref(delivery_ref):
                errors.append("Invalid delivery reference format. Use 3-30 characters with letters, numbers, hyphens, and underscores only.")
            
            # Validar fecha y hora
            is_valid_datetime, dt_iso, datetime_errors = generator.validate_datetime(
                selected_date, selected_hour, selected_minute, selected_ampm
            )
            if not is_valid_datetime:
                errors.extend(datetime_errors)
            
            # Validar items
            is_valid_items, item_list, item_errors = generator.validate_items(items_raw)
            if not is_valid_items:
                errors.extend(item_errors)
            
            # Mostrar errores si existen
            if errors:
                for error in errors:
                    st.error(error)
                st.stop()
            
            # Construir datos para el QR (SIN METADATA ADICIONAL)
            data = {
                "plate": plate.strip().upper(),
                "driverName": driver.strip().title(),
                "customer_id": customer_id.strip().upper(),
                "date_time_at_gate": dt_iso,
                "item_list": item_list
            }
            
            # Agregar campos opcionales solo si tienen valor
            if truck_type:
                data["truckType"] = truck_type
            if company.strip():
                data["company"] = company.strip()
            if delivery_ref.strip():
                data["deliveryOrderRef"] = delivery_ref.strip().upper()
            
            
            # Generar QR
            generate_qr_and_update_state(data)

else:
    # Mostrar resultado del QR
    st.markdown("### QR Code Generated:")
    
    # Centrar el QR code
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(f"data:image/png;base64,{st.session_state.qr_base64}", use_container_width=True)
    
    # Mostrar información del QR
    if st.session_state.json_str:
        data = json.loads(st.session_state.json_str)
        
        # Mostrar resumen (calculado desde los datos existentes)
        st.markdown("### Summary:")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Plate:** {data.get('plate', 'N/A')}")
            st.write(f"**Driver:** {data.get('driverName', 'N/A')}")
            st.write(f"**Customer ID:** {data.get('customer_id', 'N/A')}")
        with col2:
            # Calcular totales desde item_list
            item_list = data.get('item_list', [])
            total_items = len(item_list)
            total_quantity = sum(item.get('quantity', 0) for item in item_list)
            
            st.write(f"**Total Items:** {total_items}")
            st.write(f"**Total Quantity:** {total_quantity}")
            st.write(f"**Date/Time:** {data.get('date_time_at_gate', 'N/A')}")
    
    # Mostrar JSON completo
    with st.expander("📋 QR Content (JSON)", expanded=False):
        st.code(st.session_state.json_str, language="json")

    # Botón para volver al formulario
    col_left_back_btn, col_center_back_btn, col_right_back_btn = st.columns([1, 2, 1])
    with col_center_back_btn:
        st.button("Back to Form", on_click=return_to_form)