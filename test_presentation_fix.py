import re

def extract_presentation(name: str) -> dict | None:
    """
    Extrae y normaliza la presentación/tamaño del producto (volumen en ml, peso en g, o unidades).
    """
    text = name.lower()
    
    # 1. Litros / mililitros / cc
    match_l = re.search(r'(\d+(?:[.,]\d+)?)\s*(l|lt|litro|litros)\b', text)
    if match_l:
        val = float(match_l.group(1).replace(',', '.'))
        return {"type": "volume_ml", "value": int(val * 1000)}
        
    match_ml = re.search(r'(\d+)\s*(ml|cc|cc\.)\b', text)
    if match_ml:
        return {"type": "volume_ml", "value": int(match_ml.group(1))}

    # 2. Kilos / gramos / gr
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilos)\b', text)
    if match_kg:
        val = float(match_kg.group(1).replace(',', '.'))
        return {"type": "weight_g", "value": int(val * 1000)}

    match_g = re.search(r'(\d+)\s*(g|gr|gramos|grs)\b', text)
    if match_g:
        return {"type": "weight_g", "value": int(match_g.group(1))}

    # 3. Unidades (ej. x 3, 6 un)
    match_un = re.search(r'(?:x\s*(\d+)|(\d+)\s*un\b|(\d+)\s*unidades\b)', text)
    if match_un:
        val = match_un.group(1) or match_un.group(2) or match_un.group(3)
        return {"type": "units", "value": int(val)}

    return None

def are_presentations_compatible(off_name: str, sup_name: str) -> bool:
    p_off = extract_presentation(off_name)
    p_sup = extract_presentation(sup_name)

    if p_off and p_sup:
        if p_off["type"] == p_sup["type"]:
            return p_off["value"] == p_sup["value"]

    return True

# Pruebas de detección
test_cases = [
    ("Colet Dulce de Leche 250 ml", "Colet Dulce de Leche 1 Litro"),
    ("Yogur Fondo Durazno 180 cc", "Yogur Fondo Durazno 180 cc"),
    ("Dulce de Leche Conaprole 500g", "Dulce de Leche Conaprole 1 Kg"),
    ("Leche Entera 1L", "Leche Entera 1 Litro"),
    ("Empanadas Polar x 3 un", "Empanadas Polar x 6 un"),
]

for off, sup in test_cases:
    p1 = extract_presentation(off)
    p2 = extract_presentation(sup)
    compat = are_presentations_compatible(off, sup)
    print(f"'{off}' ({p1}) vs '{sup}' ({p2})")
    print(f"  --> Compatibles: {compat}\n")
