"""
Вспомогательные функции для работы с ИРБИС64
"""
import re
import uuid
from typing import Optional, List, Dict


def normalize_rfid(rfid: str) -> Optional[str]:
    """
    Нормализация RFID/UID в единый формат (HEX без разделителей, uppercase)
    
    Примеры:
        "AB:CD:EF:12" -> "ABCDEF12"
        "ab-cd-ef-12" -> "ABCDEF12"
        "0xABCDEF12" -> "ABCDEF12"
    """
    if not rfid:
        return None
    
    rfid = rfid.strip().upper()
    rfid = re.sub(r'[\s\-:]+', '', rfid)
    
    if rfid.startswith("0X"):
        rfid = rfid[2:]
    
    rfid = ''.join(c for c in rfid if c in '0123456789ABCDEF')
    
    return rfid if rfid else None


def insert_every2(hex_str: str, sep: str) -> str:
    """
    Вставка разделителя каждые 2 символа
    
    Пример: "ABCDEF12", ":" -> "AB:CD:EF:12"
    """
    return sep.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))


def reverse_by_byte(hex_str: str) -> str:
    """
    Реверс байтов
    
    Пример: "ABCDEF12" -> "12EFCDAB"
    """
    bytes_list = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
    return "".join(reversed(bytes_list))


def make_uid_variants(uid: str) -> List[str]:
    """
    Генерация вариантов UID для поиска в ИРБИС
    
    Возвращает список возможных форматов UID:
    - Базовый HEX
    - С разделителями : и -
    - Реверс байтов
    - Десятичное представление
    """
    hex_only = normalize_rfid(uid)
    if not hex_only:
        return [uid] if uid else []
    
    variants = []
    
    variants.append(hex_only)
    
    if len(hex_only) >= 4:
        variants.append(insert_every2(hex_only, ":"))
        variants.append(insert_every2(hex_only, "-"))
    
    rev_hex = reverse_by_byte(hex_only)
    if rev_hex != hex_only:
        variants.append(rev_hex)
        variants.append(insert_every2(rev_hex, ":"))
        variants.append(insert_every2(rev_hex, "-"))
    
    try:
        dec_value = str(int(hex_only, 16))
        variants.append(dec_value)
        variants.append(dec_value.zfill(10))
        
        if rev_hex != hex_only:
            rev_dec = str(int(rev_hex, 16))
            if rev_dec != dec_value:
                variants.append(rev_dec)
                variants.append(rev_dec.zfill(10))
    except ValueError:
        pass
    
    return variants


def parse_subfields(field_value: str) -> Dict[str, str]:
    """
    Парсинг подполей ИРБИС
    
    Пример: "^Avalue1^Bvalue2^C" -> {"A": "value1", "B": "value2", "C": ""}
    
    Структура поля 40 (выдача):
        ^A - Шифр книги
        ^B - Инвентарный номер
        ^C - Краткое описание
        ^D - Дата выдачи (YYYYMMDD)
        ^E - Дата возврата план (YYYYMMDD)
        ^F - Дата возврата факт (YYYYMMDD или "******")
        ^G - База данных (IBIS)
        ^H - RFID метка
        ^I - Оператор
        ^K - Место хранения
        ^R - Место возврата
        ^V - Место выдачи
        ^Z - GUID записи
        ^1 - Время выдачи (HHMMSS)
        ^2 - Время возврата (HHMMSS)
    """
    result = {}
    
    if not field_value:
        return result
    
    parts = field_value.split("^")
    
    for part in parts:
        if not part:
            continue
        
        code = part[0].upper()
        value = part[1:] if len(part) > 1 else ""
        result[code] = value
    
    return result


def format_subfields(subfields: Dict[str, str]) -> str:
    """
    Форматирование подполей обратно в строку ИРБИС
    
    {"A": "value1", "B": "value2"} -> "^Avalue1^Bvalue2"
    """
    parts = []
    
    for code, value in subfields.items():
        parts.append(f"^{code}{value}")
    
    return "".join(parts)


def generate_guid() -> str:
    """Генерация уникального идентификатора (для поля 40^Z)"""
    return uuid.uuid4().hex


def parse_record(text: str) -> Optional[Dict]:
    """
    Парсинг записи ИРБИС из текстового формата
    
    Возвращает словарь:
    {
        "mfn": int,
        "status": int,
        "version": int,
        "fields": {"tag": ["value1", "value2", ...], ...}
    }
    """
    if not text or not text.strip():
        return None
    
    record = {
        "mfn": 0,
        "status": 0,
        "version": 0,
        "fields": {}
    }
    
    lines = text.strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "#" in line:
            try:
                tag, value = line.split("#", 1)
                tag = tag.strip()
                if tag.isdigit():
                    if tag not in record["fields"]:
                        record["fields"][tag] = []
                    record["fields"][tag].append(value)
            except ValueError:
                continue
    
    return record


def format_record(record: Dict) -> str:
    """
    Форматирование записи обратно в текстовый формат ИРБИС
    """
    lines = []
    
    if "mfn" in record:
        lines.append(f"0#{record['mfn']}")
    
    for tag, values in record.get("fields", {}).items():
        if isinstance(values, list):
            for value in values:
                lines.append(f"{tag}#{value}")
        else:
            lines.append(f"{tag}#{values}")
    
    return "\n".join(lines)


def get_field_value(record: Dict, tag: str, default: str = "") -> str:
    """Получить первое значение поля"""
    values = record.get("fields", {}).get(tag, [])
    return values[0] if values else default


def get_field_values(record: Dict, tag: str) -> List[str]:
    """Получить все значения поля"""
    return record.get("fields", {}).get(tag, [])


def get_subfield_value(field_value: str, subfield: str, default: str = "") -> str:
    """Получить значение подполя из строки поля"""
    subfields = parse_subfields(field_value)
    return subfields.get(subfield.upper(), default)


def find_exemplar_by_rfid(record: Dict, rfid: str) -> Optional[Dict]:
    """
    Найти экземпляр книги по RFID в поле 910
    
    Поле 910:
        ^a - Статус (0=на месте, 1=выдан, C=списан, U=утерян)
        ^b - Инвентарный номер
        ^c - Дата поступления
        ^d - Место хранения
        ^h - RFID метка
    """
    rfid_normalized = normalize_rfid(rfid)
    if not rfid_normalized:
        return None
    
    rfid_variants = make_uid_variants(rfid)
    
    for field910 in get_field_values(record, "910"):
        subfields = parse_subfields(field910)
        exemplar_rfid = normalize_rfid(subfields.get("H", ""))
        
        if exemplar_rfid:
            if exemplar_rfid == rfid_normalized:
                return {
                    "status": subfields.get("A", ""),
                    "inventory": subfields.get("B", ""),
                    "date": subfields.get("C", ""),
                    "location": subfields.get("D", ""),
                    "rfid": exemplar_rfid,
                    "raw": field910,
                }
            
            for variant in rfid_variants:
                if variant.upper() == exemplar_rfid:
                    return {
                        "status": subfields.get("A", ""),
                        "inventory": subfields.get("B", ""),
                        "date": subfields.get("C", ""),
                        "location": subfields.get("D", ""),
                        "rfid": exemplar_rfid,
                        "raw": field910,
                    }
    
    return None


def format_book_brief(record: Dict) -> str:
    """Форматирование краткого описания книги"""
    author = get_field_value(record, "700", "")
    if not author:
        author = get_field_value(record, "701", "")
    
    if author:
        subfields = parse_subfields(author)
        author = subfields.get("A", "") + " " + subfields.get("B", "")
        author = author.strip()
    
    title = get_field_value(record, "200", "")
    if title:
        subfields = parse_subfields(title)
        title = subfields.get("A", "")
    
    if author and title:
        return f"{author}. {title}"
    return title or author or "Неизвестная книга"


def get_active_loans(reader_record: Dict) -> List[Dict]:
    """
    Получить список активных выдач читателя из поля 40
    (где ^F = "******")
    """
    active_loans = []
    
    for field40 in get_field_values(reader_record, "40"):
        subfields = parse_subfields(field40)
        
        return_date = subfields.get("F", "")
        if return_date == "******":
            active_loans.append({
                "rfid": subfields.get("H", ""),
                "title": subfields.get("C", ""),
                "shelfmark": subfields.get("A", ""),
                "inventory": subfields.get("B", ""),
                "issue_date": subfields.get("D", ""),
                "due_date": subfields.get("E", ""),
                "operator": subfields.get("I", ""),
                "location": subfields.get("K", ""),
                "guid": subfields.get("Z", ""),
            })
    
    return active_loans


def find_loan_by_rfid(reader_record: Dict, rfid: str) -> Optional[int]:
    """
    Найти индекс записи о выдаче по RFID книги
    Возвращает индекс в списке полей 40 или None
    """
    rfid_normalized = normalize_rfid(rfid)
    if not rfid_normalized:
        return None
    
    rfid_variants = make_uid_variants(rfid)
    
    for i, field40 in enumerate(get_field_values(reader_record, "40")):
        subfields = parse_subfields(field40)
        
        if subfields.get("F", "") != "******":
            continue
        
        loan_rfid = normalize_rfid(subfields.get("H", ""))
        if not loan_rfid:
            continue
        
        if loan_rfid == rfid_normalized:
            return i
        
        for variant in rfid_variants:
            if variant.upper() == loan_rfid:
                return i
        
        if rfid_normalized.endswith(loan_rfid) or loan_rfid.endswith(rfid_normalized):
            return i
    
    return None
