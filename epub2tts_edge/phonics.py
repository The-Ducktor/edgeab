# sentence.py

import re

# Dictionary mapping names to their phonic counterparts
_phonics = {
    "Rimuru Tempest": "Ree-moo-roo Tem-pest",
    "Rimuru": "Ree-moo-roo",
    "Veldora Tempest": "Vel-doh-rah Tem-pest",
    "Veldora": "Vel-doh-rah",
    "Shizu": "Shee-zoo",
    "Shizue Izawa": "Shee-zoo-eh Ee-zah-wah",
    "Milim Nava": "Mee-leem Nah-vah",
    "Milim": "Mee-leem",
    "Benimaru": "Beh-nee-mah-roo",
    "Shuna": "Shoo-nah",
    "Shion": "Shee-on",
    "Souei": "So-way",
    "Hakuro": "Hah-koo-roh",
    "Gobta": "Gohb-tah",
    "Ranga": "Rahng-gah",
    "Diablo": "Dee-ah-bloh",
    "Kurobe": "Koo-roh-beh",
    "Geld": "Geld",
    "Rigurd": "Ree-gurd",
    "Gabiru": "Gah-bee-roo",
    "Hinata Sakaguchi": "Hee-nah-tah Sah-kah-goo-chee",
    "Hinata": "Hee-nah-tah",
    "Karin": "Kah-rin",
    "Jura Tempest": "Joo-rah Tem-pest",
    "Gabil": "Gah-beel"
}

def phontify(text):
    """Replace character names in the text with their phonic counterparts."""
    for name, phonic in _phonics.items():
        # Use regular expression to replace names (case insensitive)
        text = re.sub(r'\b' + re.escape(name) + r'\b', phonic, text, flags=re.IGNORECASE)
    return text
