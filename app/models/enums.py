import enum


class UserRole(str, enum.Enum):
    PATIENT = "client"
    NURSE = "nurse"
    ADMIN = "admin"
   
