from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    category_name: str
    main_image_id: Optional[int] = None
    description: str
    skill: str = None

class CreateCategory(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class Category(CreateCategory):
    id: int

    class Config:
        from_attributes = True

class CreateImage(BaseModel):
    name: Optional[str] = None
    name_base64: str
    category_id: int

class Image(CreateImage):
    id: int

    class Config:
        from_attributes = True

class ReturnCategory(BaseModel):
    id: int
    category_name: str
    main_image: Optional[str] = None
    description: str
    skill: List[str]

    class Config:
        from_attributes = True

class ReturnCategories(BaseModel):
    id: int
    category_name: str
    main_image: Optional[str] = None

    class Config:
        from_attributes = True

class GetImageByCategory(BaseModel):
    category_id: int
    image_name: str


class ReturnImageWithCategory(BaseModel):
    id: int
    # Use Field with alias so that the ORM attribute 'name_base64' is mapped to 'image_base64'
    image_base64: str = Field(..., alias="name_base64")

    class Config:
        from_attributes = True
        populate_by_name = True

class ReturnCategoryWithImages(ReturnCategory):
    images: List[ReturnImageWithCategory] = []

    class Config:
        from_attributes = True

