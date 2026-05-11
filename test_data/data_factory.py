from faker import Faker
import random
import string

fake = Faker("en_IN")

@dataclass
class AgencyRegistrationData:
    username: str
    password: str
    email: str
    pan_number: str
    district: str



def generate_registration_data() -> dict:
    return {
        "username": fake.user_name().replace("-", "_"),
        "password": "Test@1234",          # keep password fixed for predictability
        "email": ...,                      # always use testmail address for OTP
        "pan": generate_pan(),
        "district": random.choice([
            "Pune", "Mumbai", "Nashik", "Nagpur", "Aurangabad"
        ]),
        "agency_name": fake.company(),
        "address": fake.address(),
        "mobile": generate_mobile(),
        "website": fake.url(),
    }


def generate_pan() -> str:
    """Generates a valid-format PAN: AAAAA9999A"""
    letters = string.ascii_uppercase
    return (
        ''.join(random.choices(letters, k=5)) +
        ''.join(random.choices(string.digits, k=4)) +
        random.choice(letters)
    )


def generate_mobile() -> str:
    """Generates a valid 10-digit Indian mobile number."""
    first_digit = random.choice(["6", "7", "8", "9"])
    rest = ''.join(random.choices(string.digits, k=9))
    return first_digit + rest




class AgencyDataFactory:
    """
    Factory that builds AgencyRegistrationData objects.
    Call .valid() for happy-path tests,
    .invalid_pan() for negative tests, etc.
    """

    @staticmethod
    def _generate_pan() -> str:
        """Generates a syntactically valid PAN: ABCDE1234F"""
        letters = random.choices(string.ascii_uppercase, k=5)
        digits  = random.choices(string.digits, k=4)
        suffix  = random.choice(string.ascii_uppercase)
        return "".join(letters) + "".join(digits) + suffix

    @staticmethod
    def _generate_password() -> str:
        """Meets: min 8 chars, uppercase, number, symbol"""
        return f"Test@{fake.numerify('####')}"

    @classmethod
    def valid(cls) -> AgencyRegistrationData:
        return AgencyRegistrationData(
            username=fake.user_name().replace("-", "")[:15],  # no spaces
            password=cls._generate_password(),
            email=fake.company_email(),
            pan_number=cls._generate_pan(),
            district="Pune",
        )

    @classmethod
    def invalid_pan(cls) -> AgencyRegistrationData:
        data = cls.valid()
        data.pan_number = "INVALID123"   # intentionally bad
        return data

    @classmethod
    def short_username(cls) -> AgencyRegistrationData:
        data = cls.valid()
        data.username = "ab"             # fails < 6 char rule
        return data

    @classmethod
    def weak_password(cls) -> AgencyRegistrationData:
        data = cls.valid()
        data.password = "password"       # no uppercase/symbol
        return data