from ninja import Schema, Field


class RegisterSchema(Schema):
    username: str = Field(..., min_length=3, max_length=150)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)
    register_as_staff: bool = Field(default=False)
    admin_invite_code: str = Field(default="", max_length=256)
