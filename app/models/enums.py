import enum


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    NURSE = "nurse"
    ADMIN = "admin"
   
