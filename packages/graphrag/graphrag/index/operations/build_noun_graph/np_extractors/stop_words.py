# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Custom list of stop words to be excluded by noun phrase extractors."""

EN_STOP_WORDS = [
    "stuff",
    "thing",
    "things",
    "bunch",
    "bit",
    "bits",
    "people",
    "person",
    "okay",
    "hey",
    "hi",
    "hello",
    "laughter",
    "oh",
]

RU_STOP_WORDS: frozenset[str] = frozenset({
    "И", "ИЛИ", "НО", "А", "В", "НА", "К", "ПО",
    "ОТ", "ДО", "С", "У", "ДЛЯ", "ЧТО", "КОТОРЫЙ",
    "ЭТОТ", "ЭТА", "ЭТО", "ЭТИ", "ТАКОЙ", "ТАК",
    "НЕ", "ТЕ", "МЫ", "ВЫ", "ОНИ", "ОН", "ОНА",
    "ЗДЕСЬ", "ТАМ", "ВСЕ", "ВСЯКИЙ", "КАЖДЫЙ",
    "МОЙ", "ТВОЙ", "СВОЙ", "ВАШ", "Наш",
    "ЭТОГО", "ЭТОЙ", "ЭТИХ", "ТАКОГО",
    "КОМУ", "КОГО", "КЕМ", "ЧЕМ", "ОКОЛО",
    "КРОМЕ", "БЕЗ", "ПОД", "ПЕРЕ", "ПРЕД",
    "ЗА", "ОБ", "РОЗ", "СРЕДИ",
})
