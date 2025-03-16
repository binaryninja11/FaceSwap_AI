import base64

from fastapi import HTTPException, UploadFile, File, Form, Depends
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from app.crud import categorycrud as crud
from app.schemas import schema
from sqlalchemy.orm import Session
from app.dependencies import get_db
from starlette.concurrency import run_in_threadpool

async def file_to_base(file: UploadFile) -> str:
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="File must be a JPEG or PNG image.")

    image_data = await file.read()

    try:
        base64_encoded = base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error encoding image to Base64: {str(e)}")

    return base64_encoded

async def base_to_file(base64_str: str) -> bytes:
    try:
        image_data = base64.b64decode(base64_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decoding Base64 image: {str(e)}")
    return image_data

async def get_category(
    category_name: str = Form(...),
    description: str= Form(...),
    skill: List[str]= Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> schema.Category:
    try:
        check = await run_in_threadpool(crud.get_category_by_name, db, category_name)
        if check:
            raise HTTPException(status_code=400, detail=f"Category '{category_name}' already exists")

        new_category = await run_in_threadpool(
            crud.create_category,
            db,
            schema.CreateCategory(
                category_name=category_name,
                description=description,
                skill=skill[0]
            )
        )

        base64_img = await file_to_base(file)

        image_main = await run_in_threadpool(
            crud.create_imge_main,
            db,
            None,  # name is None
            base64_img,
            new_category.id
        )

        # Update category with main_image_id
        new_category.main_image_id = image_main.id
        db.commit()
        db.refresh(new_category)

        return new_category
    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error {str(e)}")
