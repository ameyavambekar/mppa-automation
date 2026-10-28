"""
Maharashtra districts and talukas — as the MPPA portal itself knows them.

Extracted from the portal on 2026-10-28:
  * DISTRICT_IDS — district name -> id, from the registration / Part A
    District drop-downs (the same 36 districts plus "Other" = 999 at registration).
  * TALUKAS — district name -> talukas, from the TALUKAS constant that
    Part A (partA.php) uses to fill its Taluka drop-downs.

Part A only offers the talukas of the agency's *registered* district for a
Maharashtra head office, so test data must take its taluka from here.
Re-extract if the portal's lists change.
"""

import random

OTHER_DISTRICT = "Other"          # registration option; carries no district into Part A

DISTRICT_IDS: dict[str, str] = {
    'Ahilyanagar': '522',
    'Akola': '501',
    'Amravati': '503',
    'Beed': '523',
    'Bhandara': '506',
    'Buldhana': '500',
    'Chandrapur': '509',
    'Chhatrapati Sambhajinagar': '515',
    'Dharashiv': '525',
    'Dhule': '498',
    'Gadchiroli': '508',
    'Gondia': '507',
    'Hingoli': '512',
    'Jalgaon': '499',
    'Jalna': '514',
    'Kolhapur': '530',
    'Latur': '524',
    'Mumbai City': '519',
    'Mumbai Suburban': '518',
    'Nagpur': '505',
    'Nanded': '511',
    'Nandurbar': '497',
    'Nashik': '516',
    'Palghar': '532',
    'Parbhani': '513',
    'Pune': '521',
    'Raigad': '520',
    'Ratnagiri': '528',
    'Sangli': '531',
    'Satara': '527',
    'Sindhudurg': '529',
    'Solapur': '526',
    'Thane': '517',
    'Wardha': '504',
    'Washim': '502',
    'Yavatmal': '510',
}

TALUKAS: dict[str, list[str]] = {
    'Ahilyanagar': ['Ahilyanagar', 'Akole', 'Jamkhed', 'Karjat', 'Kopargaon', 'Nagar', 'Nevasa', 'Parner', 'Pathardi', 'Rahata', 'Rahuri', 'Sangamner', 'Shevgaon', 'Shrigonda', 'Shrirampur'],
    'Akola': ['Akola', 'Akot', 'Balapur', 'Barshitakli', 'Murtijapur', 'Patur', 'Telhara'],
    'Amravati': ['Amravati', 'Achalpur', 'Anjangaon Surji', 'Bhatkuli', 'Chandur Railway', 'Chandurbazar', 'Chikhaldara', 'Daryapur', 'Dhamangaon Railway', 'Dharni', 'Morshi', 'Nandgaon Khandeshwar', 'Teosa', 'Warud'],
    'Beed': ['Beed', 'Ambajogai', 'Ashti', 'Dharur', 'Georai', 'Kaij', 'Majalgaon', 'Parli', 'Patoda', 'Shirur Kasar', 'Wadwani'],
    'Bhandara': ['Bhandara', 'Lakhandur', 'Lakhani', 'Mohadi', 'Pauni', 'Sakoli', 'Tumsar'],
    'Buldhana': ['Buldhana', 'Chikhli', 'Deulgaon Raja', 'Jalgaon Jamod', 'Khamgaon', 'Lonar', 'Malkapur', 'Mehkar', 'Motala', 'Nandura', 'Sangrampur', 'Shegaon', 'Sindkhed Raja'],
    'Chandrapur': ['Chandrapur', 'Ballarpur', 'Bhadravati', 'Brahmapuri', 'Chimur', 'Gondpipri', 'Jiwati', 'Korpana', 'Mul', 'Nagbhid', 'Pombhurna', 'Rajura', 'Sawali', 'Sindewahi', 'Warora'],
    'Chhatrapati Sambhajinagar': ['Chhatrapati Sambhajinagar', 'Gangapur', 'Kannad', 'Khuldabad', 'Paithan', 'Phulambri', 'Sillod', 'Soegaon', 'Vaijapur'],
    'Dharashiv': ['Dharashiv', 'Bhum', 'Kalamb', 'Lohara', 'Osmanabad', 'Paranda', 'Tuljapur', 'Washi'],
    'Dhule': ['Dhule', 'Sakri', 'Shirpur', 'Sindkheda'],
    'Gadchiroli': ['Gadchiroli', 'Aheri', 'Armori', 'Bhamragad', 'Chamorshi', 'Desaiganj (Wadsa)', 'Dhanora', 'Etapalli', 'Korchi', 'Kurkheda', 'Mulchera', 'Sironcha'],
    'Gondia': ['Gondia', 'Amgaon', 'Arjuni Morgaon', 'Deori', 'Goregaon', 'Sadak Arjuni', 'Salekasa', 'Tirora'],
    'Hingoli': ['Hingoli', 'Aundha Nagnath', 'Basmath', 'Kalamnuri', 'Sengaon'],
    'Jalgaon': ['Jalgaon', 'Amalner', 'Bhadgaon', 'Bhusawal', 'Bodwad', 'Chalisgaon', 'Chopda', 'Dharangaon', 'Erandol', 'Jamner', 'Muktainagar', 'Pachora', 'Parola', 'Raver', 'Yawal'],
    'Jalna': ['Jalna', 'Ambad', 'Badnapur', 'Bhokardan', 'Ghansawangi', 'Jafrabad', 'Mantha', 'Partur'],
    'Kolhapur': ['Ajra', 'Bhudargad', 'Chandgad', 'Gadhinglaj', 'Gaganbawada', 'Hatkanangale', 'Kagal', 'Karvir', 'Panhala', 'Radhanagari', 'Shahuwadi', 'Shirol'],
    'Latur': ['Latur', 'Ahmedpur', 'Ausa', 'Chakur', 'Deoni', 'Jalkot', 'Nilanga', 'Renapur', 'Shirur Anantpal', 'Udgir'],
    'Mumbai City': ['Mumbai City'],
    'Mumbai Suburban': ['Andheri', 'Borivali', 'Kurla'],
    'Nagpur': ['Nagpur', 'Bhiwapur', 'Hingna', 'Kalameshwar', 'Kamptee', 'Katol', 'Kuhi', 'Mauda', 'Narkhed', 'Parseoni', 'Ramtek', 'Savner', 'Umred'],
    'Nanded': ['Nanded', 'Ardhapur', 'Bhokar', 'Biloli', 'Deglur', 'Dharmabad', 'Hadgaon', 'Himayatnagar', 'Kandhar', 'Kinwat', 'Loha', 'Mahur', 'Mudkhed', 'Mukhed', 'Naigaon', 'Umri'],
    'Nandurbar': ['Nandurbar', 'Akkalkuwa', 'Akrani (Dhadgaon)', 'Nawapur', 'Shahada', 'Taloda'],
    'Nashik': ['Nashik', 'Baglan (Satana)', 'Chandwad', 'Deola', 'Dindori', 'Igatpuri', 'Kalwan', 'Malegaon', 'Nandgaon', 'Niphad', 'Peint', 'Sinnar', 'Surgana', 'Trimbakeshwar', 'Yeola'],
    'Palghar': ['Palghar', 'Dahanu', 'Jawhar', 'Mokhada', 'Talasari', 'Vasai', 'Vikramgad', 'Wada'],
    'Parbhani': ['Parbhani', 'Gangakhed', 'Jintur', 'Manwath', 'Palam', 'Pathri', 'Purna', 'Sailu', 'Sonpeth'],
    'Pune': ['Ambegaon', 'Baramati', 'Bhor', 'Daund', 'Haveli', 'Indapur', 'Junnar', 'Khed', 'Maval', 'Mulshi', 'Pune City', 'Purandar', 'Shirur', 'Velhe'],
    'Raigad': ['Alibag', 'Karjat', 'Khalapur', 'Mahad', 'Mangaon', 'Mhasla', 'Murud', 'Panvel', 'Poladpur', 'Roha', 'Shrivardhan', 'Sudhagad', 'Tala', 'Uran', '\\u092a\\u0947\\u0923'],
    'Ratnagiri': ['Ratnagiri', 'Chiplun', 'Dapoli', 'Guhagar', 'Khed', 'Lanja', 'Mandangad', 'Rajapur', 'Sangameshwar'],
    'Sangli': ['Atpadi', 'Jat', 'Kadegaon', 'Kavathe Mahankal', 'Khanapur (Vita)', 'Miraj', 'Palus', 'Shirala', 'Tasgaon', 'Walwa'],
    'Satara': ['Satara', 'Jaoli', 'Karad', 'Khandala', 'Khatav', 'Koregaon', 'Mahabaleshwar', 'Man', 'Patan', 'Phaltan', 'Wai'],
    'Sindhudurg': ['Devgad', 'Dodamarg', 'Kankavli', 'Kudal', 'Malvan', 'Sawantwadi', 'Vaibhavwadi', 'Vengurla'],
    'Solapur': ['Akkalkot', 'Barshi', 'Karmala', 'Madha', 'Malshiras', 'Mangalvedhe', 'Mohol', 'Pandharpur', 'Sangole', 'Solapur North', 'Solapur South'],
    'Thane': ['Thane', 'Ambernath', 'Bhiwandi', 'Kalyan', 'Murbad', 'Shahapur', 'Ulhasnagar'],
    'Wardha': ['Wardha', 'Arvi', 'Ashti', 'Deoli', 'Hinganghat', 'Karanja', 'Samudrapur', 'Seloo'],
    'Washim': ['Washim', 'Karanja', 'Malegaon', 'Mangrulpir', 'Manora', 'Risod'],
    'Yavatmal': ['Yavatmal', 'Arni', 'Babulgaon', 'Darwha', 'Digras', 'Ghatanji', 'Kalamb', 'Kelapur (Pandharkawada)', 'Mahagaon', 'Maregaon', 'Ner', 'Pusad', 'Ralegaon', 'Umarkhed', 'Wani', 'Zari Jamani'],
}

MH_PINCODE_RANGE = (400000, 445999)   # Part A accepts only this range for Maharashtra


def random_district() -> str:
    """A random listed Maharashtra district (never "Other")."""
    return random.choice(sorted(DISTRICT_IDS))


def random_taluka(district: str) -> str:
    """A random taluka that Part A offers for district."""
    return random.choice(TALUKAS[district])


def random_mh_pincode() -> str:
    """A random pincode inside Part A's Maharashtra range."""
    return str(random.randint(*MH_PINCODE_RANGE))


def is_listed_district(district) -> bool:
    """True for one of the 36 districts (False for "Other", blank or None)."""
    return district in TALUKAS
