from pydantic import BaseModel, Field
class User(BaseModel):
    id: int = Field(primary_key=True)

for name, field in User.model_fields.items():
    print(name, field.json_schema_extra, getattr(field, "json_schema_extra", None))
